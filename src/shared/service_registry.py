"""Service registry — pure shared, no infrastructure imports. Set by Dependencies."""

from __future__ import annotations

from typing import Any

_registry: dict[str, Any] = {}


def set_service(name: str, instance: Any) -> None:
    _registry[name] = instance


def get_service(name: str) -> Any | None:
    return _registry.get(name)


def clear() -> None:
    _registry.clear()
