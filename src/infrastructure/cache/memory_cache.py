"""
In-memory caching implementation for the financial insight agent.

Provides fast, local caching with LRU eviction and TTL management.
"""

import atexit
import logging
import threading
import time
from typing import Any
from collections import OrderedDict

logger = logging.getLogger(__name__)


class MemoryCache:
    """In-memory cache implementation with LRU eviction and TTL."""

    def __init__(
        self, max_size: int = 1000, default_ttl_hours: int = 1, cleanup_interval_minutes: int = 10
    ):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum number of items to store
            default_ttl_hours: Default TTL in hours
            cleanup_interval_minutes: Cleanup interval in minutes
        """
        self.max_size = max_size
        self.default_ttl_hours = default_ttl_hours
        self.cleanup_interval = cleanup_interval_minutes * 60  # Convert to seconds

        # Thread-safe storage
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_order: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.RLock()

        # Cleanup thread with stop event for graceful shutdown
        self._stop_event = threading.Event()
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()

        atexit.register(self.close)

        logger.info(
            f"Initialized MemoryCache with max_size={max_size}, default_ttl={default_ttl_hours}h"
        )

    def _get_key(self, key: str, namespace: str = "cache") -> str:
        """Generate full cache key with namespace."""
        return f"{namespace}:{key}"

    def _is_expired(self, item: dict[str, Any]) -> bool:
        """Check if cache item is expired."""
        if "expires_at" not in item:
            return False
        return time.time() > item["expires_at"]

    def _evict_lru(self) -> None:
        """Evict least recently used items if cache is full."""
        with self._lock:
            excess = len(self._cache) - self.max_size + 1
            if excess <= 0:
                return
            keys_to_evict = []
            for _ in range(min(excess, self.max_size // 5)):
                if not self._access_order:
                    break
                keys_to_evict.append(next(iter(self._access_order)))
            for k in keys_to_evict:
                self._access_order.pop(k, None)
                self._cache.pop(k, None)
            if keys_to_evict:
                logger.debug("Evicted %d LRU items", len(keys_to_evict))

    def _cleanup_expired(self) -> None:
        """Background cleanup of expired items."""
        while not self._stop_event.is_set():
            try:
                self._stop_event.wait(timeout=self.cleanup_interval)
                if self._stop_event.is_set():
                    break
                self._cleanup_expired_items()
            except Exception as e:
                logger.error("Error in cleanup thread: %s", e)

    def _cleanup_expired_items(self) -> None:
        """Remove expired items from cache."""
        with self._lock:
            expired_keys = [key for key in self._cache if self._is_expired(self._cache[key])]

            for key in expired_keys:
                self._cache.pop(key, None)
                self._access_order.pop(key, None)

            if expired_keys:
                logger.debug("Cleaned up %d expired items", len(expired_keys))

    def get(self, key: str, namespace: str = "cache") -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            Cached value or None if not found/expired
        """
        full_key = self._get_key(key, namespace)

        with self._lock:
            item = self._cache.get(full_key)

            if item is None:
                return None

            if self._is_expired(item):
                # Remove expired item
                self._cache.pop(full_key, None)
                self._access_order.pop(full_key, None)
                return None

            # Update access order (move to end)
            self._access_order.move_to_end(full_key, last=True)

            return item["value"]

    def set(
        self, key: str, value: Any, ttl_hours: int | None = None, namespace: str = "cache"
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_hours: TTL in hours (uses default if None)
            namespace: Cache namespace

        Returns:
            True if successful, False otherwise
        """
        full_key = self._get_key(key, namespace)
        ttl_hours = ttl_hours or self.default_ttl_hours

        with self._lock:
            # Evict LRU items if needed
            self._evict_lru()

            # Store item
            item = {
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + (ttl_hours * 3600),
                "ttl_hours": ttl_hours,
            }

            self._cache[full_key] = item
            self._access_order[full_key] = time.time()

            logger.debug("Cached key %s with TTL %sh", key, ttl_hours)
            return True

    def delete(self, key: str, namespace: str = "cache") -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            True if successful, False otherwise
        """
        full_key = self._get_key(key, namespace)

        with self._lock:
            removed = self._cache.pop(full_key, None) is not None
            self._access_order.pop(full_key, None)

            if removed:
                logger.debug("Deleted key: %s", key)

            return removed

    def exists(self, key: str, namespace: str = "cache") -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            True if key exists and not expired, False otherwise
        """
        full_key = self._get_key(key, namespace)

        with self._lock:
            item = self._cache.get(full_key)

            if item is None:
                return False

            if self._is_expired(item):
                self._cache.pop(full_key, None)
                self._access_order.pop(full_key, None)
                return False

            return True

    def flush(self, namespace: str | None = None) -> bool:
        """
        Flush cache.

        Args:
            namespace: If provided, only flush keys in this namespace

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if namespace:
                # Remove keys in specific namespace
                keys_to_remove = [key for key in self._cache if key.startswith(f"{namespace}:")]
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    self._access_order.pop(key, None)
            else:
                # Clear all
                self._cache.clear()
                self._access_order.clear()

            logger.info("Flushed cache namespace: %s", namespace or "all")
            return True

    def info(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            active_items = 0
            expired_items = 0

            for item in self._cache.values():
                if self._is_expired(item):
                    expired_items += 1
                else:
                    active_items += 1

            return {
                "cache_type": "memory",
                "max_size": self.max_size,
                "current_size": len(self._cache),
                "active_items": active_items,
                "expired_items": expired_items,
                "default_ttl_hours": self.default_ttl_hours,
                "cleanup_interval_minutes": self.cleanup_interval // 60,
                "memory_usage_mb": self._estimate_memory_usage(),
            }

    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB by recursively measuring nested objects."""
        import sys

        def _deep_size(obj: Any, seen: set | None = None) -> int:
            if seen is None:
                seen = set()
            obj_id = id(obj)
            if obj_id in seen:
                return 0
            seen.add(obj_id)
            size = sys.getsizeof(obj)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    size += _deep_size(k, seen) + _deep_size(v, seen)
            elif isinstance(obj, (list, tuple, set, frozenset)):
                for item in obj:
                    size += _deep_size(item, seen)
            return size

        try:
            total_size = sum(_deep_size(item) for item in self._cache.values())
            return round(total_size / (1024 * 1024), 2)
        except Exception:
            return 0.0

    def close(self) -> None:
        """Close cache with graceful thread shutdown."""
        self._stop_event.set()
        if self._cleanup_thread.is_alive() and self._cleanup_thread is not threading.current_thread():
            self._cleanup_thread.join(timeout=5)
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
        logger.info("Memory cache closed")

    def __del__(self) -> None:
        """Fallback cleanup if close() wasn't called explicitly."""
        self._stop_event.set()


def get_memory_cache() -> MemoryCache | None:
    """Get memory cache instance from Dependencies container."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    return deps.memory_cache if deps is not None else None
