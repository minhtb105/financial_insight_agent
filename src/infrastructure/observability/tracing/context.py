"""Context propagation for traces across async tasks and worker threads.

``span_stack_var`` holds an immutable tuple of open spans; the top of the
stack is the current parent. Threads created via ``contextvars.copy_context()``
(see ``multi_query_runner``) inherit the stack snapshot, so child spans
created inside worker threads resolve the correct parent.
"""

from __future__ import annotations

from contextvars import ContextVar

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_stack_var: ContextVar[tuple] = ContextVar("span_stack", default=())


def current_trace_id() -> str | None:
    return trace_id_var.get()


def current_parent_span_id() -> str | None:
    stack = span_stack_var.get()
    if not stack:
        return None
    return stack[-1].span_id
