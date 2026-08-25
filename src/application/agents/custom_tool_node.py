"""
Custom ToolNode with dedup + retry for the ReAct agent.

Replaces LangGraph's built-in ToolNode. Handles three scenarios:

  1. New tool call  → execute, cache result
  2. Duplicate call + prev success → return cached result (zero API cost)
  3. Duplicate call + prev error (TOOL_ERR#) → retry up to MAX_RETRIES

The public ``execute_one()`` method encapsulates the dedup/cache/retry
logic so both ``__call__`` (reads from AIMessage.tool_calls) and
external callers like ``_action_node`` (reads from ``next_tool_call``)
can reuse the same logic without duplication.
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage, BaseMessage

from infrastructure.observability.tracing import SpanKind, get_tracer

logger = logging.getLogger(__name__)

_TOOL_ERR_PREFIX = "TOOL_ERR#"
_MAX_RETRIES = 2


class CustomToolNode:
    """Drop-in replacement for ``ToolNode`` from ``langgraph.prebuilt``.

    Usage::

        tools = ALL_TOOLS
        tool_node = CustomToolNode(tools)   # instead of ToolNode(tools)

    The ``execute_one()`` method can be called externally by the agent's
    action node to process a single tool call from ``next_tool_call``
    while keeping dedup/cache/retry logic in one place.
    """

    def __init__(self, tools: list) -> None:
        self.tools_by_name: dict[str, Any] = {t.name: t for t in tools}

    # ------------------------------------------------------------------
    # Public interface (called by LangGraph as a node)
    # ------------------------------------------------------------------

    def __call__(self, state: dict) -> dict:
        messages: list[BaseMessage] = state.get("messages", [])
        last = messages[-1] if messages else None
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {"messages": []}

        history: set[str] = set(state.get("tool_call_history", []))
        cache: dict[str, str] = dict(state.get("tool_call_cache", {}))
        retries: dict[str, int] = dict(state.get("tool_call_retries", {}))

        tool_messages: list[ToolMessage] = []
        for tc in last.tool_calls:
            tool_call_id = tc.get("id", "")
            tool_name = tc.get("name", "")
            content = self.execute_one(tc, history, cache, retries)
            tool_messages.append(
                ToolMessage(content=content, tool_call_id=tool_call_id, name=tool_name)
            )

        return {
            "messages": tool_messages,
            "tool_call_history": list(history),
            "tool_call_cache": cache,
            "tool_call_retries": retries,
        }

    # ------------------------------------------------------------------
    # Reusable execution: used by both __call__ and external action node
    # ------------------------------------------------------------------

    def execute_one(
        self,
        tool_call: dict,
        history: set[str],
        cache: dict[str, str],
        retries: dict[str, int],
    ) -> str:
        """Execute a single tool call with dedup / cache / retry.

        Parameters
        ----------
        tool_call : dict
            Must have keys ``name``, ``args``, and ``id``.
        history : set[str]
            Set of fingerprints already seen (mutated in place).
        cache : dict[str, str]
            Map fingerprint → result content (mutated in place).
        retries : dict[str, int]
            Map fingerprint → retry count (mutated in place).

        Returns
        -------
        str
            Tool result, or ``TOOL_ERR#...`` on failure.
        """
        fingerprint = self._fingerprint(tool_call)
        tool_name = tool_call.get("name", "")

        if fingerprint not in history:
            with self._trace_span(tool_name, tool_call, "first_call") as span:
                content = self._execute(tool_call)
                if span is not None:
                    span.outputs = content
            history.add(fingerprint)
            cache[fingerprint] = content
            retries[fingerprint] = 0
            logger.info(
                "Tool executed: %s %s",
                tool_name,
                "(first call)" if not self._has_error(content) else "(first call, error)",
            )
        else:
            cached = cache.get(fingerprint, "")
            retry_count = retries.get(fingerprint, 0)
            if self._has_error(cached) and retry_count < _MAX_RETRIES:
                with self._trace_span(tool_name, tool_call, f"retry_{retry_count + 1}") as span:
                    content = self._execute(tool_call)
                    if span is not None:
                        span.outputs = content
                cache[fingerprint] = content
                retries[fingerprint] = retry_count + 1
                logger.info(
                    "Tool retried: %s (attempt %d/%d)",
                    tool_name,
                    retry_count + 1,
                    _MAX_RETRIES,
                )
            else:
                content = cached
                logger.info(
                    "Tool cached: %s (%s)",
                    tool_name,
                    "error, retries exhausted" if self._has_error(cached) else "success",
                )

        return content

    @staticmethod
    def _trace_span(tool_name: str, tool_call: dict, invocation: str):
        """Open a TOOL span for a real (non-cached) execution."""
        tracer = get_tracer()
        return tracer.start_span(
            name=tool_name or "unknown_tool",
            kind=SpanKind.TOOL,
            attributes={"invocation": invocation, "tool_call_id": tool_call.get("id", "")},
            inputs=tool_call.get("args", {}),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fingerprint(tc: dict) -> str:
        args = tc.get("args", {})
        return f"{tc.get('name', '')}|{json.dumps(args, sort_keys=True)}"

    @staticmethod
    def _has_error(content: str) -> bool:
        return _TOOL_ERR_PREFIX in str(content)

    def _execute(self, tc: dict) -> str:
        tool_name = tc.get("name", "")
        tool = self.tools_by_name.get(tool_name)
        if not tool:
            return f"{_TOOL_ERR_PREFIX}UNKNOWN Unknown tool: {tool_name}"
        try:
            result = tool.invoke(tc.get("args", {}))
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return f"{_TOOL_ERR_PREFIX}UNKNOWN {e}"
