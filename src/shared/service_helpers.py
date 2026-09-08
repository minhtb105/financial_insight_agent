"""Central factory for service handlers — eliminates 12× duplicate handle_* wrappers.

Each ``handle_*_query`` previously duplicated::

    from shared.service_registry import get_service
    svc = get_service("name")
    if svc is None: raise RuntimeError(...)
    return svc.handle_query(...)

This module provides a single helper ``call_service`` that all wrappers delegate to.
"""

from typing import Any


def call_service(service_name: str, **kwargs: Any) -> dict[str, Any]:
    """Lookup *service_name* via registry and invoke ``handle_query``.

    Raises:
        RuntimeError: if service not initialized (mirrors original wrappers).
    """
    from shared.service_registry import get_service

    svc = get_service(service_name)
    if svc is None:
        raise RuntimeError(f"Service '{service_name}' not initialized — call init_deps()")
    # All services expose handle_query; method dispatch is uniform.
    return svc.handle_query(**kwargs)  # type: ignore[operator]


def make_handler(service_name: str):
    """Return a thin wrapper ``handle_query`` for *service_name*.

    Useful for MCP tool registration where a callable is needed.
    """

    def handler(**kwargs: Any) -> dict[str, Any]:
        return call_service(service_name, **kwargs)

    handler.__name__ = f"handle_{service_name}_query"
    return handler
