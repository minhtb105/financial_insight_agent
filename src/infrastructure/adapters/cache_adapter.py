"""Cache adapter implementing CachePort."""

from __future__ import annotations

from typing import Any

from shared.ports.cache_port import CachePort


class CacheAdapter(CachePort):
    def __init__(self, manager: Any):
        self._m = manager

    def get(self, key: str) -> Any | None:
        return self._m.get(key)

    def set(self, key: str, value: Any, ttl_hours: float = 1.0) -> None:
        self._m.set(key, value, ttl_hours=ttl_hours)

    def delete(self, key: str) -> None:
        try:
            self._m.delete(key)
        except Exception:
            pass
