import os
import asyncio
import ipaddress
import threading
from collections import deque
from contextlib import asynccontextmanager, suppress
import time

from fastapi import FastAPI, APIRouter, Request, HTTPException
from interfaces.api.routes.traces import router as traces_router
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from infrastructure.dependencies import init_deps, shutdown_deps
from infrastructure.observability import get_logger
from infrastructure.observability.metrics.collector import get_metrics_collector
from infrastructure.observability.tracing import SpanKind, get_tracer
from application.agents.agent import StockAgent
from infrastructure.guardrails.pipeline import GuardrailPipeline

_MAX_REQUEST_BODY = 1_048_576  # 1 MB

_MAX_QUERY_LENGTH = 1000

agent: StockAgent | None = None


_request_logger = get_logger("api")
_guardrail_pipeline: GuardrailPipeline | None = None

# Global IP-based rate limiter for endpoints without guardrails (health, ping)
# NOTE: In-memory only — does not survive restarts and not shared across workers.
# For multi-worker deployments, replace with Redis-backed rate limiter.
_ip_request_counts: dict[str, deque[float]] = {}
_ip_lock: asyncio.Lock = asyncio.Lock()
_IP_RATE_LIMIT = 60  # requests
_IP_RATE_WINDOW = 60  # seconds
_IP_MAX_IPS = 100_000  # prevent unbounded memory growth


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            ip = real_ip.strip()
        elif request.client:
            ip = request.client.host
        else:
            return "unknown"
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        return "unknown"


async def _check_global_rate_limit(client_ip: str) -> None:
    if client_ip == "unknown":
        return
    async with _ip_lock:
        now = time.time()
        window_start = now - _IP_RATE_WINDOW
        if client_ip not in _ip_request_counts:
            if len(_ip_request_counts) >= _IP_MAX_IPS:
                return
            _ip_request_counts[client_ip] = deque()
        counts = _ip_request_counts[client_ip]
        while counts and counts[0] < window_start:
            counts.popleft()
        if len(counts) >= _IP_RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
        counts.append(now)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=_MAX_QUERY_LENGTH,
        description="Vietnamese stock market question",
    )


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Agent response")
    request_id: str = Field("", description="Request identifier")
    latency_ms: float = Field(0.0, description="Processing time (ms)")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error description")
    error_type: str = Field("unknown_error", description="Error type")
    request_id: str = Field("", description="Request identifier")


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Server status")
    agent_ready: bool = Field(False, description="Whether the agent is ready")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_error(detail: str, error_type: str, request_id: str, status_code: int = 400):
    if status_code >= 500:
        _request_logger.error(
            "Server error: %s", detail,
            extra={"error_type": error_type, "request_id": request_id},
            exc_info=True,
        )
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            detail=detail, error_type=error_type, request_id=request_id
        ).model_dump(),
    )


def _sse_error_event(detail: str, error_type: str, request_id: str) -> str:
    err = ErrorResponse(detail=detail, error_type=error_type, request_id=request_id)
    return f"event: error\ndata: {err.model_dump_json()}\n\ndata: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global agent, _guardrail_pipeline
    try:
        init_deps()
    except Exception as e:
        _request_logger.error("Dependencies init failed", extra={"error": str(e)})
    try:
        agent = StockAgent()
        _request_logger.info("Agent initialized successfully")
    except Exception as e:
        _request_logger.error("Agent init failed", extra={"error": str(e)})
        agent = None

    try:
        _guardrail_pipeline = GuardrailPipeline()
        _request_logger.info("Guardrail pipeline initialized successfully")
    except Exception as e:
        _request_logger.error("Guardrail init failed", extra={"error": str(e)})
        _guardrail_pipeline = None

    if agent is None:
        _request_logger.warning("Starting server without agent — /ask-stream endpoint will return 503")

    yield

    shutdown_deps()


app = FastAPI(
    title="Financial Insight Agent API",
    description="REST API for a Vietnamese stock market analysis agent. "
    "Supports price lookup, technical indicators, company info, comparison, ranking, "
    "financial ratios, news/sentiment, and portfolio management.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

_allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip() for o in _allowed_origins_str.split(",") if o.strip()]
if not _allowed_origins:
    _request_logger.warning("ALLOWED_ORIGINS not set — CORS restricted to same-origin only")


# ---------------------------------------------------------------------------
# API versioning
# ---------------------------------------------------------------------------

api_router = APIRouter(prefix="/api/v1")

# Guardrail-managed paths: rate limiting handled by GuardrailPipeline
_GUARDRAIL_PATHS = frozenset({"/api/v1/ask-stream"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


class RequestBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.method in ("GET", "HEAD", "DELETE"):
            return await call_next(request)
        if request.url.path in _GUARDRAIL_PATHS:
            return await call_next(request)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_REQUEST_BODY:
            raise HTTPException(status_code=413, detail="Request body too large.")
        body = await request.body()
        if len(body) > _MAX_REQUEST_BODY:
            raise HTTPException(status_code=413, detail="Request body too large.")
        response = await call_next(request)
        return response


app.add_middleware(RequestBodySizeMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        response = await call_next(request)
        if "X-Content-Type-Options" not in response.headers:
            response.headers["X-Content-Type-Options"] = "nosniff"
        if "X-Frame-Options" not in response.headers:
            response.headers["X-Frame-Options"] = "DENY"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    request_id = _request_logger.start_request()
    request.state.request_id = request_id
    start_time = time.time()
    tracer = get_tracer()
    with tracer.start_span(
        f"http {request.method} {request.url.path}",
        SpanKind.HTTP,
        attributes={"method": request.method, "path": request.url.path},
        inputs={"query": request.url.query[:300] if request.url.query else None},
    ) as span:
        try:
            # Global rate limiter covers only non-guardrail paths (/health, /ping, etc.).
            # Guardrail-managed paths (/api/v1/ask-stream) are rate-limited by
            # GuardrailPipeline.RateLimiter instead — never both on the same endpoint.
            if request.url.path not in ("/health", "/ping", *_GUARDRAIL_PATHS):
                await _check_global_rate_limit(_get_client_ip(request))
            response = await call_next(request)
            duration = time.time() - start_time
            metrics_collector = get_metrics_collector()
            if metrics_collector and not isinstance(response, StreamingResponse):
                metrics_collector.record_request_metrics(
                    request_type=request.url.path,
                    duration=duration,
                    success=response.status_code < 500,
                )
            if not isinstance(response, StreamingResponse):
                status = "completed" if response.status_code < 500 else "error"
                _request_logger.end_request(status=status)
            if span is not None:
                span.attributes["status_code"] = getattr(response, "status_code", None)
            return response
        except HTTPException as exc:
            _request_logger.end_request(status="error")
            if span is not None:
                span.attributes["status_code"] = exc.status_code
                span.attributes["http_exception"] = str(exc.detail)[:200]
            raise
        except Exception as exc:
            duration = time.time() - start_time
            metrics_collector = get_metrics_collector()
            if metrics_collector:
                metrics_collector.record_request_metrics(
                    request_type=request.url.path,
                    duration=duration,
                    success=False,
                    error_type=type(exc).__name__,
                )
            _request_logger.end_request(status="error", error=str(exc))
            return _build_error(
                detail="Internal server error",
                error_type="internal_error",
                request_id=getattr(request.state, "request_id", ""),
                status_code=500,
            )


# ---------------------------------------------------------------------------
# Guardrail dependency
# ---------------------------------------------------------------------------


async def check_guardrails(query: str, request: Request):
    if _guardrail_pipeline is None:
        return
    client_ip = _get_client_ip(request)
    result = _guardrail_pipeline.check(query, client_ip)
    if not result.passed:
        _request_logger.warning(
            "Guardrail blocked query",
            extra={
                "reason": result.reason,
                "status_code": result.status_code,
            },
        )
        raise HTTPException(status_code=result.status_code, detail="Query rejected.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------



@api_router.post(
    "/ask-stream",
    summary="Gửi câu hỏi chứng khoán (streaming)",
    description="Nhận câu hỏi tiếng Việt và trả về câu trả lời theo dạng SSE stream.",
    responses={
        200: {"description": "SSE stream response"},
        400: {"description": "Query rỗng hoặc không hợp lệ"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def ask_stock_agent_stream(body: QueryRequest, request: Request):
    request_id = request.state.request_id
    start_time = time.time()

    if agent is None:

        async def no_agent_stream():
            try:
                yield _sse_error_event("Agent not initialized", "agent_unavailable", request_id)
            finally:
                _request_logger.end_request(status="error")

        return StreamingResponse(no_agent_stream(), media_type="text/event-stream")

    await check_guardrails(body.query, request)

    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty or only whitespace")

    try:

        async def stream_response():
            end_requested = False
            try:
                full_response = ""
                loop = asyncio.get_running_loop()
                async_queue = asyncio.Queue(maxsize=64)
                cancel_event = threading.Event()

                def _produce():
                    try:
                        for chunk in agent.run_stream(body.query, request_id=request_id):
                            if cancel_event.is_set():
                                return
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    async_queue.put(chunk), loop
                                ).result()
                            except Exception:
                                cancel_event.set()
                                return
                    except Exception:
                        pass
                    finally:
                        with suppress(Exception):
                            asyncio.run_coroutine_threadsafe(
                                async_queue.put(None), loop
                            ).result()

                loop.run_in_executor(None, _produce)

                while True:
                    chunk = await async_queue.get()
                    if chunk is None:
                        break
                    if await request.is_disconnected():
                        cancel_event.set()
                        return
                    full_response += chunk
                    yield f"event: chunk\ndata: {chunk}\n\n"

                if not await request.is_disconnected():
                    latency_ms = round((time.time() - start_time) * 1000, 2)
                    final = QueryResponse(
                        answer=full_response,
                        request_id=request_id,
                        latency_ms=latency_ms,
                    )
                    yield f"event: final\ndata: {final.model_dump_json()}\n\n"
                end_requested = True
                _request_logger.end_request(
                    status="completed" if not await request.is_disconnected() else "disconnected"
                )
                metrics_collector = get_metrics_collector()
                if metrics_collector and not await request.is_disconnected():
                    metrics_collector.record_request_metrics(
                        request_type="/ask-stream",
                        duration=latency_ms / 1000,
                        success=True,
                    )
            except GeneratorExit:
                if not end_requested:
                    cancel_event.set()
                    _request_logger.end_request(status="disconnected")
                raise
            except Exception:
                if not end_requested:
                    cancel_event.set()
                    _request_logger.end_request(status="error")
                    yield _sse_error_event("Stream processing error", "stream_error", request_id)

        return StreamingResponse(stream_response(), media_type="text/event-stream")
    except Exception as e:
        _request_logger.error(
            "Stream failed",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )

        async def error_stream():
            try:
                yield _sse_error_event("Stream processing error", "stream_error", request_id)
            finally:
                _request_logger.end_request(status="error")

        return StreamingResponse(error_stream(), media_type="text/event-stream")


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra trạng thái server",
    description="Trả về trạng thái server và thông tin agent.",
)
async def health():
    return JSONResponse(
        content=HealthResponse(status="ok", agent_ready=agent is not None).model_dump(),
        headers={"Cache-Control": "no-cache"},
    )


@app.get(
    "/ping",
    summary="Ping server",
    description="Kiểm tra server còn sống.",
)
async def ping():
    return JSONResponse(
        content={"status": "ok"},
        headers={"Cache-Control": "no-cache"},
    )

api_router.include_router(traces_router)
app.include_router(api_router)
