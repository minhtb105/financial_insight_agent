"""Self-contained tracing system: traces, spans, tool-call tracing, LLM metrics."""

__all__ = [
    "JSONLExporter",
    "Span",
    "SpanKind",
    "TraceStore",
    "Tracer",
    "TracingCallbackHandler",
    "current_trace_id",
    "get_tracer",
    "init_tracing",
    "reset_tracer",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "Span": ".models",
        "SpanKind": ".models",
        "safe_json": ".models",
        "TraceStore": ".storage",
        "JSONLExporter": ".storage",
        "Tracer": ".tracer",
        "init_tracing": ".tracer",
        "get_tracer": ".tracer",
        "reset_tracer": ".tracer",
        "TracingCallbackHandler": ".langchain_handler",
        "current_trace_id": ".context",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
