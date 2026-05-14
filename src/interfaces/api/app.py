from contextlib import asynccontextmanager
import time
from typing import Optional
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.dependencies import init_deps, shutdown_deps
from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var
from infrastructure.observability.metrics.collector import get_metrics_collector
from application.agents.agent import StockAgent
from infrastructure.guardrails.pipeline import GuardrailPipeline

_MAX_QUERY_LENGTH = 1000

agent: Optional[StockAgent] = None
_request_logger = get_logger("api")
_guardrail_pipeline: Optional[GuardrailPipeline] = None

# Global IP-based rate limiter for endpoints without guardrails (health, ping)
_ip_request_counts: dict[str, list[float]] = defaultdict(list)
_IP_RATE_LIMIT = 60  # requests
_IP_RATE_WINDOW = 60  # seconds


def _check_global_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - _IP_RATE_WINDOW
    counts = _ip_request_counts[client_ip]
    # Prune old entries
    while counts and counts[0] < window_start:
        counts.pop(0)
    if len(counts) >= _IP_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    counts.append(now)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=_MAX_QUERY_LENGTH,
                       description="Câu hỏi tiếng Việt về chứng khoán")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời từ agent")
    query_type: str = Field("unknown", description="Loại truy vấn đã xác định")
    confidence: float = Field(0.0, description="Độ tin cậy của kết quả phân tích")
    request_id: str = Field("", description="Mã định danh request")
    latency_ms: float = Field(0.0, description="Thời gian xử lý (ms)")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Mô tả lỗi")
    error_type: str = Field("unknown_error", description="Loại lỗi")
    request_id: str = Field("", description="Mã định danh request")


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Trạng thái server")
    agent_ready: bool = Field(False, description="Agent đã sẵn sàng")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _build_error(detail: str, error_type: str, request_id: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            detail=detail, error_type=error_type, request_id=request_id
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, _guardrail_pipeline
    init_deps()
    agent = StockAgent()
    _guardrail_pipeline = GuardrailPipeline()
    yield
    shutdown_deps()


app = FastAPI(
    title="Financial Insight Agent API",
    description="REST API cho Agent phân tích câu hỏi chứng khoán tiếng Việt. "
                "Hỗ trợ tra cứu giá, chỉ báo kỹ thuật, thông tin công ty, so sánh, xếp hạng, "
                "chỉ số tài chính, tin tức và danh mục đầu tư.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    request_id = _request_logger.start_request()
    request.state.request_id = request_id
    start_time = time.time()
    try:
        _check_global_rate_limit(_get_client_ip(request))
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
        return response
    except HTTPException:
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
        raise HTTPException(
            status_code=result.status_code,
            detail=result.reason,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/ask",
    response_model=QueryResponse,
    summary="Gửi câu hỏi chứng khoán",
    description="Nhận câu hỏi tiếng Việt về chứng khoán và trả về câu trả lời "
                "từ agent với metadata kèm theo.",
    responses={
        200: {"description": "Thành công", "model": QueryResponse},
        400: {"description": "Query rỗng hoặc không hợp lệ"},
        422: {"description": "Query quá dài hoặc sai format"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Lỗi server"},
    },
)
async def ask_stock_agent(body: QueryRequest, request: Request):
    request_id = request.state.request_id
    start_time = time.time()

    await check_guardrails(body.query, request)

    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty or only whitespace")

    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        response_text = agent.run(body.query, request_id=request_id)
    except Exception as e:
        _request_logger.error("Agent run failed", extra={
            "request_id": request_id,
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Agent processing error: {e}")

    latency_ms = round((time.time() - start_time) * 1000, 2)
    query_type = getattr(agent, "_last_parsed_query", {}).get("query_type", "unknown")
    confidence = getattr(agent, "_last_confidence", 0.0)

    return QueryResponse(
        answer=response_text,
        query_type=query_type,
        confidence=confidence,
        request_id=request_id,
        latency_ms=latency_ms,
    )


@app.post(
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

    await check_guardrails(body.query, request)

    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty or only whitespace")

    if agent is None:
        async def no_agent_stream():
            yield f"data: {ErrorResponse(detail='Agent not initialized', error_type='agent_unavailable', request_id=request_id).model_dump_json()}\n\n"
        return StreamingResponse(no_agent_stream(), media_type="text/event-stream")

    try:
        async def stream_response():
            full_response = ""
            for chunk in agent.run_stream(body.query, request_id=request_id):
                full_response += chunk
                yield f"data: {chunk}\n\n"

            latency_ms = round((time.time() - start_time) * 1000, 2)
            query_type = getattr(agent, "_last_parsed_query", {}).get("query_type", "unknown")
            confidence = getattr(agent, "_last_confidence", 0.0)
            final = QueryResponse(
                answer=full_response,
                query_type=query_type,
                confidence=confidence,
                request_id=request_id,
                latency_ms=latency_ms,
            )
            yield f"data: {final.model_dump_json()}\n\n"
            _request_logger.end_request(status="completed")

        return StreamingResponse(stream_response(), media_type="text/event-stream")
    except Exception as e:
        _request_logger.error("Stream failed", extra={
            "request_id": request_id,
            "error": str(e),
        })

        async def error_stream():
            err = ErrorResponse(detail=str(e), error_type="stream_error", request_id=request_id)
            yield f"data: {err.model_dump_json()}\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra trạng thái server",
    description="Trả về trạng thái server và thông tin agent.",
)
async def health():
    return HealthResponse(status="ok", agent_ready=agent is not None)


@app.get(
    "/ping",
    summary="Ping server",
    description="Kiểm tra server còn sống.",
)
async def ping():
    return {"status": "ok"}