"""Core Tracer: span lifecycle, context management, and metrics emission.

Usage (context-managed)::

    tracer = get_tracer()
    with tracer.start_span("agent.run", SpanKind.AGENT, inputs={"query": q}) as span:
        span.attributes["num_sub_queries"] = 2
        ...

Usage (manual, for LangChain callbacks)::

    span = tracer.begin_span(name, kind, trace_id=..., parent_span_id=..., ...)
    ...
    tracer.finish_span(span)
"""

from __future__ import annotations

import os
import time
import uuid
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from infrastructure.observability.logging.logger import get_logger, request_id_var

from .context import current_parent_span_id, span_stack_var, trace_id_var
from .models import SPAN_STATUS_ERROR, Span, SpanKind, safe_json
from .storage import JSONLExporter, TraceStore

logger = get_logger("observability.tracing")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip())
    except (ValueError, AttributeError):
        return default


class Tracer:
    """Central tracing facade. One instance per process."""

    def __init__(
        self,
        store: TraceStore | None = None,
        jsonl_exporter: JSONLExporter | None = None,
        enabled: bool = True,
        max_content_chars: int = 2000,
    ):
        self.store = store
        self.jsonl_exporter = jsonl_exporter
        self.enabled = enabled and (store is not None or jsonl_exporter is not None)
        self.max_content_chars = max_content_chars
        self._metrics_registered = False

    # ------------------------------------------------------------------
    # Context-managed API
    # ------------------------------------------------------------------

    @contextmanager
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.NODE,
        attributes: dict[str, Any] | None = None,
        inputs: Any = None,
    ) -> Iterator[Span | None]:
        """Open a span bound to the ambient trace context; auto-close on exit."""
        if not self.enabled:
            yield None
            return

        parent_stack = span_stack_var.get()
        parent = parent_stack[-1] if parent_stack else None
        tid = trace_id_var.get()
        set_trace_var = tid is None
        if tid is None:
            tid = str(uuid.uuid4())

        span = Span(
            trace_id=tid,
            span_id=uuid.uuid4().hex,
            name=name,
            kind=kind,
            parent_span_id=parent.span_id if parent else None,
            request_id=request_id_var.get(),
            started_at=time.time(),
            inputs=self._truncate(inputs),
        )
        if attributes:
            span.attributes.update(self._truncate_deep(attributes))

        token_stack = span_stack_var.set((*parent_stack, span))
        token_tid = None
        if set_trace_var:
            token_tid = trace_id_var.set(tid)
        try:
            yield span
        except Exception as exc:
            span.status = SPAN_STATUS_ERROR
            span.error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            span_stack_var.reset(token_stack)
            if token_tid is not None:
                trace_id_var.reset(token_tid)
            self.finish_span(span)

    # ------------------------------------------------------------------
    # Manual API (used by TracingCallbackHandler)
    # ------------------------------------------------------------------

    def begin_span(  # noqa: PLR0917
        self,
        name: str,
        kind: SpanKind = SpanKind.NODE,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        request_id: str | None = None,
        attributes: dict[str, Any] | None = None,
        inputs: Any = None,
    ) -> Span | None:
        if not self.enabled:
            return None
        span = Span(
            trace_id=trace_id or trace_id_var.get() or str(uuid.uuid4()),
            span_id=uuid.uuid4().hex,
            name=name,
            kind=kind,
            parent_span_id=(
                parent_span_id
                if parent_span_id is not None
                else current_parent_span_id()
            ),
            request_id=request_id or request_id_var.get(),
            started_at=time.time(),
            inputs=self._truncate(inputs),
        )
        if attributes:
            span.attributes.update(self._truncate_deep(attributes))
        return span

    def finish_span(self, span: Span | None) -> None:
        if span is None:
            return
        if span.ended_at is None:
            span.ended_at = time.time()
            span.duration_ms = round((span.ended_at - span.started_at) * 1000, 2)
        try:
            self._persist(span)
            self._emit_metrics(span)
        except Exception:
            logger.exception("Failed to persist span %s", span.span_id)

    def _persist(self, span: Span) -> None:
        d = span.to_dict()
        if self.store is not None:
            inputs_json = safe_json(self._truncate(span.inputs), 0)
            outputs_json = safe_json(self._truncate(span.outputs), 0)
            attributes_json = safe_json(self._truncate_deep(span.attributes), 0)
            self.store.record_span(
                d, inputs_json, outputs_json, attributes_json,
                is_root=span.parent_span_id is None,
            )
        if self.jsonl_exporter is not None:
            self.jsonl_exporter.append(d)

    def _emit_metrics(self, span: Span) -> None:
        try:
            from infrastructure.observability.metrics.collector import get_metrics_collector

            collector = get_metrics_collector()
            if collector is None:
                return
            self._ensure_metric_defs(collector)
            labels_base = {"span_kind": span.kind.value}
            if span.kind == SpanKind.LLM:
                llm_labels = {"model": span.model or "unknown",
                              "provider": span.provider or "unknown",
                              "status": span.status}
                collector.increment_counter("tracing_llm_calls_total", labels=llm_labels)
                if span.prompt_tokens:
                    collector.increment_counter(
                        "tracing_llm_tokens_total", value=span.prompt_tokens,
                        labels={"type": "prompt", "model": span.model or "unknown"},
                    )
                if span.completion_tokens:
                    collector.increment_counter(
                        "tracing_llm_tokens_total", value=span.completion_tokens,
                        labels={"type": "completion", "model": span.model or "unknown"},
                    )
                if span.duration_ms is not None:
                    collector.observe_histogram(
                        "tracing_llm_latency_ms", span.duration_ms,
                        labels={"model": span.model or "unknown"},
                    )
            elif span.kind == SpanKind.TOOL:
                tool_labels = {"tool": span.name, "status": span.status}
                collector.increment_counter("tracing_tool_calls_total", labels=tool_labels)
                if span.duration_ms is not None:
                    collector.observe_histogram(
                        "tracing_tool_latency_ms", span.duration_ms,
                        labels={"tool": span.name},
                    )
            elif span.duration_ms is not None:
                collector.observe_histogram(
                    "tracing_span_duration_ms", span.duration_ms, labels=labels_base
                )
        except Exception:
            logger.debug("Metrics emission skipped", extra={"span": span.name})

    @staticmethod
    def _ensure_metric_defs(collector) -> None:
        from infrastructure.observability.metrics.collector import MetricDefinition

        for name, desc, mtype in [
            ("tracing_llm_calls_total", "LLM calls observed by tracer", "counter"),
            ("tracing_llm_tokens_total", "LLM tokens observed by tracer", "counter"),
            ("tracing_tool_calls_total", "Tool calls observed by tracer", "counter"),
            ("tracing_llm_latency_ms", "LLM call latency (ms)", "histogram"),
            ("tracing_tool_latency_ms", "Tool execution latency (ms)", "histogram"),
            ("tracing_span_duration_ms", "Generic span duration (ms)", "histogram"),
        ]:
            if name not in collector.metric_definitions:
                collector.register_metric(MetricDefinition(name, desc, mtype))

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def _truncate(self, value: Any) -> Any:
        if isinstance(value, str):
            limit = self.max_content_chars
            if limit > 0 and len(value) > limit:
                return value[:limit] + f"...[truncated {len(value) - limit} chars]"
            return value
        return self._truncate_deep(value)

    def _truncate_deep(self, value: Any, depth: int = 0) -> Any:
        if depth > 4:
            return str(value)[:200]
        if isinstance(value, dict):
            return {k: self._truncate_deep(v, depth + 1) for k, v in list(value.items())[:50]}
        if isinstance(value, (list, tuple)):
            items = [self._truncate_deep(v, depth + 1) for v in value[:30]]
            if len(value) > 30:
                items.append(f"...[{len(value) - 30} more]")
            return items
        if isinstance(value, str):
            return self._truncate(value)
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:200]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_tracer_lock = threading.RLock()
_tracer: Tracer | None = None


def init_tracing(
    db_path: str | None = None,
    enabled: bool | None = None,
) -> Tracer:
    """Create/reset the process-wide tracer from environment configuration."""
    global _tracer
    with _tracer_lock:
        store = None
        exporter = None
        is_enabled = _env_bool("TRACING_ENABLED", True) if enabled is None else enabled
        if is_enabled:
            path = db_path or os.getenv("TRACING_DB_PATH") or "data/traces/traces.db"
            try:
                store = TraceStore(path)
            except Exception:
                logger.exception("TraceStore init failed — tracing disabled")
                store = None
            if _env_bool("TRACING_JSONL_ENABLED", False):
                jsonl_path = os.getenv("TRACING_JSONL_PATH", "data/traces/traces.jsonl")
                try:
                    exporter = JSONLExporter(jsonl_path)
                except Exception:
                    logger.exception("JSONL exporter init failed")
            max_chars = _env_int("TRACE_MAX_CONTENT_CHARS", 2000)
            _tracer = Tracer(
                store=store,
                jsonl_exporter=exporter,
                enabled=is_enabled and store is not None,
                max_content_chars=max_chars,
            )
        else:
            _tracer = Tracer(enabled=False)
        logger.info(
            "Tracing initialized",
            extra={
                "enabled": _tracer.enabled,
                "db_path": str(store.db_path) if store else None,
                "jsonl": exporter is not None,
            },
        )
        return _tracer


def get_tracer() -> Tracer:
    """Return the singleton tracer, initializing it lazily on first access."""
    global _tracer
    if _tracer is None:
        with _tracer_lock:
            if _tracer is None:
                return init_tracing()
    return _tracer


def reset_tracer() -> None:
    """Reset the singleton (for tests)."""
    global _tracer
    with _tracer_lock:
        _tracer = None
