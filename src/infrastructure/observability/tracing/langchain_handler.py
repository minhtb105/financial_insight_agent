"""LangChain callback handler mirroring LLM / graph-node runs into tracing spans.

Attach an instance via ``config={"callbacks": [TracingCallbackHandler()]}``
when invoking the LangGraph app. Chat-model runs become ``llm`` spans
(with model, provider, and token usage); LangGraph node executions become
``node`` spans (identified by the ``langgraph_node`` metadata key).

Tool-call tracing is handled separately in ``CustomToolNode._execute`` so it
also covers cache hits and retries that never reach LangChain callbacks.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import BaseCallbackHandler

from infrastructure.observability.logging.logger import get_logger

from .models import SPAN_STATUS_ERROR, Span, SpanKind
from .context import span_stack_var
from .tracer import Tracer, get_tracer

if TYPE_CHECKING:
    from langchain_core.outputs import LLMResult

logger = get_logger("observability.tracing.handler")


def _model_info_from_response(response: Any) -> dict[str, Any]:
    """Extract (model_name, provider, usage) from an LLMResult."""
    info: dict[str, Any] = {"model": None, "provider": None,
                            "prompt_tokens": None, "completion_tokens": None,
                            "total_tokens": None}
    llm_output = getattr(response, "llm_output", None) or {}
    usage = llm_output.get("token_usage") or {}
    model = llm_output.get("model_name")

    if not usage:
        try:
            gen = response.generations[0][0]
            meta = getattr(getattr(gen, "message", None), "response_metadata", None) or {}
            usage = (
                meta.get("token_usage")
                or meta.get("usage")
                or getattr(gen, "usage_metadata", None)
                or {}
            )
            if isinstance(usage, dict) and "input_tokens" in usage:
                usage = {
                    "prompt_tokens": usage.get("input_tokens"),
                    "completion_tokens": usage.get("output_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                }
            model = model or meta.get("model_name")
        except (IndexError, AttributeError):
            pass

    if isinstance(usage, dict):
        info["prompt_tokens"] = usage.get("prompt_tokens")
        info["completion_tokens"] = usage.get("completion_tokens")
        info["total_tokens"] = usage.get("total_tokens")

    if model:
        lowered = str(model).lower()
        info["provider"] = "groq" if "groq" in lowered or "llama" in lowered else "openai"
        info["model"] = str(model)
    return info


def _serialize_messages(messages: Any, max_chars: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        for m in messages or []:
            for single in (m if isinstance(m, list) else [m]):
                role = getattr(single, "type", type(single).__name__)
                content = getattr(single, "content", "")
                out.append({
                    "role": role,
                    "content": content[:max_chars] if isinstance(content, str) else str(content)[:max_chars],
                })
    except Exception:
        return [{"role": "unknown", "content": "<unserializable>"}]
    return out


class TracingCallbackHandler(BaseCallbackHandler):
    """Converts LangChain run events into tracer spans keyed by run_id."""

    def __init__(self, tracer: Tracer | None = None):
        self._tracer = tracer or get_tracer()
        self._runs: dict[Any, Span] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_parent_span(self, parent_run_id: Any) -> Span | None:
        with self._lock:
            return self._runs.get(parent_run_id)

    def _ambient_parent(self) -> Span | None:
        stack = span_stack_var.get()
        return stack[-1] if stack else None

    def _pop(self, run_id: Any) -> Span | None:
        with self._lock:
            return self._runs.pop(run_id, None)

    def _store_ref(self, run_id: Any, span: Span | None) -> None:
        if span is not None:
            with self._lock:
                self._runs[run_id] = span

    def _open_span(  # noqa: PLR0917
        self,
        name: str,
        kind: SpanKind,
        run_id: Any,
        parent_run_id: Any | None,
        metadata: dict[str, Any] | None = None,
        inputs: Any = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Create a span whose trace/parent derive from the LangChain run tree."""
        parent_span = self._resolve_parent_span(parent_run_id)
        if parent_span is None:
            parent_span = self._ambient_parent()
        trace_id = (
            (metadata or {}).get("trace_id")
            or (parent_span.trace_id if parent_span else None)
        )
        span = self._tracer.begin_span(
            name=name,
            kind=kind,
            trace_id=trace_id,
            parent_span_id=parent_span.span_id if parent_span else None,
            attributes=attributes,
            inputs=inputs,
        )
        self._store_ref(run_id, span)

    # ------------------------------------------------------------------
    # Chat model events → LLM spans
    # ------------------------------------------------------------------

    def on_chat_model_start(
        self, serialized: dict[str, Any] | None, messages: list,
        *, run_id: Any, parent_run_id: Any | None = None,
        metadata: dict[str, Any] | None = None, **kwargs: Any,
    ) -> None:
        if not self._tracer.enabled:
            return
        try:
            name = "chat_model"
            if serialized and serialized.get("id"):
                name = str(serialized["id"][-1])
            self._open_span(
                name=name,
                kind=SpanKind.LLM,
                run_id=run_id,
                parent_run_id=parent_run_id,
                metadata=metadata,
                attributes={"langgraph_node": (metadata or {}).get("langgraph_node")},
                inputs=_serialize_messages(
                    messages, self._tracer.max_content_chars // 4
                ),
            )
        except Exception:
            logger.exception("on_chat_model_start tracing failed")

    def on_llm_end(self, response: LLMResult, *, run_id: Any, **kwargs: Any) -> None:
        span = self._pop(run_id)
        if span is None:
            return
        try:
            info = _model_info_from_response(response)
            span.model = info["model"]
            span.provider = info["provider"]
            span.prompt_tokens = info["prompt_tokens"]
            span.completion_tokens = info["completion_tokens"]
            span.total_tokens = info["total_tokens"]
            try:
                first = response.generations[0][0]
                text = getattr(first, "text", "") or ""
                if not text:
                    msg = getattr(first, "message", None)
                    text = str(getattr(msg, "content", ""))
                span.outputs = text[: self._tracer.max_content_chars]
            except (IndexError, AttributeError):
                span.outputs = None
        except Exception:
            logger.exception("on_llm_end tracing failed")
        finally:
            self._tracer.finish_span(span)

    def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        span = self._pop(run_id)
        if span is None:
            return
        span.status = SPAN_STATUS_ERROR
        span.error = f"{type(error).__name__}: {error}"
        self._tracer.finish_span(span)

    # ------------------------------------------------------------------
    # Graph node events → NODE spans
    # ------------------------------------------------------------------

    def on_chain_start(
        self, serialized: dict[str, Any] | None, inputs: dict[str, Any],
        *, run_id: Any, parent_run_id: Any | None = None,
        metadata: dict[str, Any] | None = None, **kwargs: Any,
    ) -> None:
        if not self._tracer.enabled:
            return
        try:
            node_name = (metadata or {}).get("langgraph_node")
            if not node_name:
                return  # skip non-graph chain noise (wrappers, sequences…)
            self._open_span(
                name=str(node_name),
                kind=SpanKind.NODE,
                run_id=run_id,
                parent_run_id=parent_run_id,
                metadata=metadata,
                inputs=None,
                attributes={
                    "langgraph_step": (metadata or {}).get("langgraph_step"),
                    "run_name": kwargs.get("name") or "",
                },
            )
        except Exception:
            logger.exception("on_chain_start tracing failed")

    def on_chain_end(self, outputs: dict[str, Any], *, run_id: Any, **kwargs: Any) -> None:
        span = self._pop(run_id)
        if span is None:
            return
        try:
            if isinstance(outputs, dict):
                interesting = {
                    k: v for k, v in outputs.items()
                    if k in ("iterations", "next_tool_call", "tool_call_history")
                }
                span.attributes.update(interesting or {})
        except Exception:
            logger.exception("on_chain_end tracing failed")
        finally:
            self._tracer.finish_span(span)

    def on_chain_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        span = self._pop(run_id)
        if span is None:
            return
        span.status = SPAN_STATUS_ERROR
        span.error = f"{type(error).__name__}: {error}"
        self._tracer.finish_span(span)

    # ------------------------------------------------------------------
    # Tool events — intentionally disabled.
    # Tool-call tracing is owned by CustomToolNode._trace_span, which also
    # covers cache hits and retries that never surface as callback events.
    # Enabling these would double-record every execution once LangGraph
    # propagates callbacks into tool.invoke().
    # ------------------------------------------------------------------

    def on_tool_start(
        self, serialized: dict[str, Any] | None, input_str: str,
        *, run_id: Any, parent_run_id: Any | None = None,
        inputs: dict[str, Any] | None = None, **kwargs: Any,
    ) -> None:
        return

    def on_tool_end(self, output: Any, *, run_id: Any, **kwargs: Any) -> None:
        return

    def on_tool_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        return
