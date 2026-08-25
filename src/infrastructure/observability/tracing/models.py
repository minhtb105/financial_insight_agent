"""
Trace/span data model for the self-contained tracing system.

A trace is a tree of spans sharing one ``trace_id``. Every span records
timing, status, (optionally truncated) inputs/outputs, and LLM-specific
metadata such as model, provider, token usage, and prompt version.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from typing import Any

SPAN_STATUS_OK = "ok"
SPAN_STATUS_ERROR = "error"


class SpanKind(enum.StrEnum):
    AGENT = "agent"
    NODE = "node"
    LLM = "llm"
    TOOL = "tool"
    GUARDRAIL = "guardrail"
    HTTP = "http"


@dataclass
class Span:
    """A single timed operation within a trace."""

    trace_id: str
    span_id: str
    name: str
    kind: SpanKind
    parent_span_id: str | None = None
    request_id: str | None = None
    started_at: float = 0.0
    ended_at: float | None = None
    duration_ms: float | None = None
    status: str = SPAN_STATUS_OK
    error: str | None = None
    inputs: Any = None
    outputs: Any = None
    attributes: dict[str, Any] = field(default_factory=dict)
    model: str | None = None
    provider: str | None = None
    prompt_name: str | None = None
    prompt_version: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value if isinstance(self.kind, SpanKind) else str(self.kind),
            "request_id": self.request_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "attributes": self.attributes,
            "model": self.model,
            "provider": self.provider,
            "prompt_name": self.prompt_name,
            "prompt_version": self.prompt_version,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


def safe_json(value: Any, max_chars: int) -> str | None:
    """Serialize a value to a truncated JSON string, never raising."""
    if value is None:
        return None
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError, RecursionError):
        text = str(value)
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars] + f"...[truncated {len(text) - max_chars} chars]"
    return text
