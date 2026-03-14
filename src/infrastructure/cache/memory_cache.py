"""
In-memory caching implementation for the financial insight agent.

Provides fast, local caching with LRU eviction and TTL management.
"""

import json
import logging
import threading
import time
from typing import Any, Optional, Dict, List
from collections import OrderedDict


logger = logging.getLogger(__name__)


class MemoryCache:
    """In-memory cache implementation with LRU eviction and TTL."""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_hours: int = 1,
        cleanup_interval_minutes: int = 10
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
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.RLock()
        
        # Cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"Initialized MemoryCache with max_size={max_size}, default_ttl={default_ttl_hours}h")
    
    def _serialize(self, data: Any) -> str:
        """Serialize data to JSON string."""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize data: {e}")
            return json.dumps({"error": "Serialization failed", "data": str(data)})
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to Python object."""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to deserialize data: {e}")
            return None
    
    def _get_key(self, key: str, namespace: str = "cache") -> str:
        """Generate full cache key with namespace."""
        return f"{namespace}:{key}"
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if cache item is expired."""
        if "expires_at" not in item:
            return False
        return time.time() > item["expires_at"]
    
    def _evict_lru(self) -> None:
        """Evict least recently used items if cache is full."""
        with self._lock:
            while len(self._cache) >= self.max_size and self._access_order:
                # Remove oldest item (first in OrderedDict)
                oldest_key = next(iter(self._access_order))
                self._access_order.pop(oldest_key)
                self._cache.pop(oldest_key, None)
                logger.debug(f"Evicted LRU item: {oldest_key}")
    
    def _cleanup_expired(self) -> None:
        """Background cleanup of expired items."""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired_items()
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
    
    def _cleanup_expired_items(self) -> None:
        """Remove expired items from cache."""
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, item in self._cache.items():
                if self._is_expired(item):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._cache.pop(key, None)
                self._access_order.pop(key, None)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired items")
    
    def get(self, key: str, namespace: str = "cache") -> Optional[Any]:
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
            
            return self._deserialize(item["value"])
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_hours: Optional[int] = None,
        namespace: str = "cache"
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
                "value": self._serialize(value),
                "created_at": time.time(),
                "expires_at": time.time() + (ttl_hours * 3600),
                "ttl_hours": ttl_hours
            }
            
            self._cache[full_key] = item
            self._access_order[full_key] = time.time()
            
            logger.debug(f"Cached key {key} with TTL {ttl_hours}h")
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
                logger.debug(f"Deleted key: {key}")
            
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
    
    def keys(self, pattern: str = "*", namespace: str = "cache") -> List[str]:
        """
        Get all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports simple glob patterns)
            namespace: Cache namespace
            
        Returns:
            List of matching keys
        """
        with self._lock:
            if pattern == "*":
                # Fast path for wildcard
                return [key.replace(f"{namespace}:", "") for key in self._cache.keys() if key.startswith(f"{namespace}:")]
            
            # Pattern matching
            import fnmatch
            matching_keys = []
            
            for key in self._cache.keys():
                if key.startswith(f"{namespace}:") and fnmatch.fnmatch(key, f"{namespace}:{pattern}"):
                    matching_keys.append(key.replace(f"{namespace}:", ""))
            
            return matching_keys
    
    def ttl(self, key: str, namespace: str = "cache") -> Optional[int]:
        """
        Get TTL for key in seconds.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            TTL in seconds, or None if key doesn't exist or has no TTL
        """
        full_key = self._get_key(key, namespace)
        
        with self._lock:
            item = self._cache.get(full_key)
            
            if item is None:
                return None
            
            if "expires_at" not in item:
                return None
            
            remaining = item["expires_at"] - time.time()
            return max(0, int(remaining))
    
    def expire(self, key: str, ttl_hours: int, namespace: str = "cache") -> bool:
        """
        Set TTL for existing key.
        
        Args:
            key: Cache key
            ttl_hours: TTL in hours
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        full_key = self._get_key(key, namespace)
        
        with self._lock:
            item = self._cache.get(full_key)
            
            if item is None:
                return False
            
            item["expires_at"] = time.time() + (ttl_hours * 3600)
            item["ttl_hours"] = ttl_hours
            
            logger.debug(f"Updated TTL for key {key} to {ttl_hours}h")
            return True
    
    def flush(self, namespace: Optional[str] = None) -> bool:
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
                keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{namespace}:")]
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    self._access_order.pop(key, None)
            else:
                # Clear all
                self._cache.clear()
                self._access_order.clear()
            
            logger.info(f"Flushed cache namespace: {namespace or 'all'}")
            return True
    
    def info(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            current_time = time.time()
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
                "memory_usage_mb": self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        try:
            import sys
            total_size = 0
            for item in self._cache.values():
                total_size += sys.getsizeof(item["value"])
            return round(total_size / (1024 * 1024), 2)
        except ImportError:
            return 0.0
    
    def close(self) -> None:
        """Close cache (cleanup resources)."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
        logger.info("Memory cache closed")


# Global cache instance
_memory_cache_instance: Optional[MemoryCache] = None


def get_memory_cache() -> Optional[MemoryCache]:
    """Get global memory cache instance."""
    global _memory_cache_instance
    if _memory_cache_instance is None:
        try:
            _memory_cache_instance = MemoryCache()
        except Exception as e:
            logger.error(f"Failed to create memory cache instance: {e}")
            _memory_cache_instance = None
    return _memory_cache_instance


def set_memory_cache_instance(cache: MemoryCache) -> None:
    """Set global memory cache instance (for testing)."""
    global _memory_cache_instance
    _memory_cache_instance = cache