"""CachePort — abstraction for caching."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CachePort(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl_hours: float = 1.0) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...
