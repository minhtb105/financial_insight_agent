"""
Multi-tier cache manager for the financial insight agent.

Implements a hierarchical caching strategy with automatic promotion/demotion
between cache tiers based on access patterns and data importance.
"""

import logging
import time
from typing import Any
from dataclasses import dataclass

from infrastructure.cache.redis_cache import RedisCache
from infrastructure.cache.memory_cache import MemoryCache
from infrastructure.cache.config import CacheTier
from infrastructure.resilience.circuit_breaker import create_circuit_breaker

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics for monitoring and optimization."""

    tier: CacheTier
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_access_time: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def avg_access_time(self) -> float:
        """Calculate average access time in milliseconds."""
        return (
            (self.total_access_time / (self.hits + self.misses) * 1000)
            if (self.hits + self.misses) > 0
            else 0.0
        )


class CacheManager:
    """
    Multi-tier cache manager with intelligent data placement and migration.

    Features:
    - L1: In-memory cache (fastest, volatile)
    - L2: Redis cache (fast, persistent)
    - Automatic promotion/demotion based on access patterns
    - Circuit breaker for failed tiers
    - Metrics collection and monitoring
    """

    def __init__(
        self,
        enable_l1: bool = True,
        enable_l2: bool = True,
        l1_max_size: int = 500,
        l1_ttl_hours: float = 0.5,
        l2_ttl_hours: int = 2,
        circuit_breaker_timeout: int = 30,
        l1_cache: Any | None = None,
        l2_cache: Any | None = None,
    ):
        self.enable_l1 = enable_l1
        self.enable_l2 = enable_l2

        self.circuit_breaker_timeout = circuit_breaker_timeout

        # Initialize cache tiers — use shared instances if provided
        self.l1_cache = l1_cache
        if self.enable_l1 and self.l1_cache is None:
            self.l1_cache = MemoryCache(max_size=l1_max_size, default_ttl_hours=l1_ttl_hours)
        if not self.enable_l1:
            self.l1_cache = None

        self.l2_cache = l2_cache
        if self.enable_l2 and self.l2_cache is None:
            self.l2_cache = RedisCache(ttl_hours=l2_ttl_hours)
        if not self.enable_l2:
            self.l2_cache = None

        # Statistics
        self.stats = {
            CacheTier.L1_MEMORY: CacheStats(CacheTier.L1_MEMORY),
            CacheTier.L2_REDIS: CacheStats(CacheTier.L2_REDIS),
        }

        logger.info("Initialized CacheManager with tiers: L1=%s, L2=%s", enable_l1, enable_l2)

        self.circuit_breakers = {
            CacheTier.L1_MEMORY: create_circuit_breaker(
                name="cache_l1",
                recovery_timeout=circuit_breaker_timeout,
            ),
            CacheTier.L2_REDIS: create_circuit_breaker(
                name="cache_l2",
                recovery_timeout=circuit_breaker_timeout,
            ),
        }

    def _get_cache_for_tier(self, tier: CacheTier):
        """Get cache instance for specific tier."""
        if tier == CacheTier.L1_MEMORY:
            return self.l1_cache
        elif tier == CacheTier.L2_REDIS:
            return self.l2_cache
        else:
            return None

    def _is_circuit_open(self, tier: CacheTier) -> bool:
        """Check if circuit breaker is open for tier."""
        cb = self.circuit_breakers.get(tier)
        return cb is not None and cb.is_open()

    def _record_access(
        self, tier: CacheTier, operation: str, duration: float, success: bool = True
    ):
        """Record cache access statistics."""
        stats = self.stats[tier]

        if operation == "get":
            if success:
                stats.hits += 1
            else:
                stats.misses += 1
        elif operation == "set":
            stats.sets += 1
        elif operation == "delete":
            stats.deletes += 1

        stats.total_access_time += duration

    def get(self, key: str, namespace: str = "cache") -> Any | None:
        """
        Get value from cache with multi-tier lookup.

        Tries L1 -> L2 -> L3 in order, promoting successful hits to higher tiers.
        """
        start_time = time.time()

        # Try L1 first (if enabled and circuit not open)
        if self.enable_l1 and self.l1_cache and not self._is_circuit_open(CacheTier.L1_MEMORY):
            try:
                value = self.l1_cache.get(key, namespace)
                duration = time.time() - start_time

                if value is not None:
                    self._record_access(CacheTier.L1_MEMORY, "get", duration, success=True)
                    logger.debug("L1 cache hit for key %s", key)
                    return value

                self._record_access(CacheTier.L1_MEMORY, "get", duration, success=False)

            except Exception as e:
                self._record_access(CacheTier.L1_MEMORY, "get", duration, success=False)
                self._handle_circuit_breaker(CacheTier.L1_MEMORY, e)
                logger.warning("L1 cache error for key %s: %s", key, e)

        # Try L2 (if enabled and circuit not open)
        if self.enable_l2 and self.l2_cache and not self._is_circuit_open(CacheTier.L2_REDIS):
            try:
                l2_start = time.time()
                value = self.l2_cache.get(key, namespace)
                duration = time.time() - l2_start

                if value is not None:
                    self._record_access(CacheTier.L2_REDIS, "get", duration, success=True)
                    logger.debug("L2 cache hit for key %s", key)
                    if (
                        self.enable_l1
                        and self.l1_cache
                        and not self._is_circuit_open(CacheTier.L1_MEMORY)
                    ):
                        try:
                            self.l1_cache.set(
                                key, value, ttl_hours=0.25, namespace=namespace
                            )
                        except Exception as e:
                            logger.warning("L2->L1 promotion failed for key %s: %s", key, e)
                    return value

                self._record_access(CacheTier.L2_REDIS, "get", duration, success=False)

            except Exception as e:
                self._record_access(CacheTier.L2_REDIS, "get", duration, success=False)
                self._handle_circuit_breaker(CacheTier.L2_REDIS, e)
                logger.warning("L2 cache error for key %s: %s", key, e)

        # Cache miss
        total_duration = time.time() - start_time
        logger.debug("Cache miss for key %s (total duration: %.3fs)", key, total_duration)
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_hours: int | None = None,
        namespace: str = "cache",
        force_tier: CacheTier | None = None,
    ) -> bool:
        """
        Set value in cache with intelligent tier placement.

        Args:
            key: Cache key
            value: Value to cache
            ttl_hours: TTL in hours
            namespace: Cache namespace
            force_tier: Force placement in specific tier (for manual control)
        """
        start_time = time.time()

        success = False

        # Determine target tiers
        target_tiers = []
        if force_tier:
            target_tiers = [force_tier]
        else:
            # Default: store in all enabled tiers
            if self.enable_l1:
                target_tiers.append(CacheTier.L1_MEMORY)
            if self.enable_l2:
                target_tiers.append(CacheTier.L2_REDIS)

        for tier in target_tiers:
            if self._is_circuit_open(tier):
                continue

            cache_instance = self._get_cache_for_tier(tier)
            if not cache_instance:
                continue

            try:
                result = cache_instance.set(key, value, ttl_hours=ttl_hours, namespace=namespace)
                duration = time.time() - start_time

                if result:
                    self._record_access(tier, "set", duration, success=True)
                    success = True
                    logger.debug("Successfully set key %s in %s", key, tier.value)
                else:
                    self._record_access(tier, "set", duration, success=False)

            except Exception as e:
                duration = time.time() - start_time
                self._record_access(tier, "set", duration, success=False)
                self._handle_circuit_breaker(tier, e)
                logger.error("Failed to set key %s in %s: %s", key, tier.value, e)

        return success

    def delete(self, key: str, namespace: str = "cache") -> bool:
        """Delete key from all cache tiers."""
        success = False

        for tier in [CacheTier.L1_MEMORY, CacheTier.L2_REDIS]:
            if not self._get_cache_for_tier(tier) or self._is_circuit_open(tier):
                continue

            try:
                cache_instance = self._get_cache_for_tier(tier)
                result = cache_instance.delete(key, namespace)

                if result:
                    self._record_access(tier, "delete", 0, success=True)
                    success = True
                    logger.debug("Deleted key %s from %s", key, tier.value)

            except Exception as e:
                self._record_access(tier, "delete", 0, success=False)
                self._handle_circuit_breaker(tier, e)
                logger.error("Failed to delete key %s from %s: %s", key, tier.value, e)

        return success

    def _handle_circuit_breaker(self, tier: CacheTier, error: Exception):
        """Handle circuit breaker logic for failed cache tier."""
        cb = self.circuit_breakers.get(tier)
        if cb:
            cb.record_failure()
        logger.warning("Cache circuit breaker recorded failure for %s: %s", tier.value, error)

    def exists(self, key: str, namespace: str = "cache") -> bool:
        """Check if key exists in any cache tier."""
        for tier in [CacheTier.L1_MEMORY, CacheTier.L2_REDIS]:
            if not self._get_cache_for_tier(tier) or self._is_circuit_open(tier):
                continue

            try:
                cache_instance = self._get_cache_for_tier(tier)
                if cache_instance.exists(key, namespace):
                    return True

            except Exception as e:
                self._handle_circuit_breaker(tier, e)
                logger.error("Failed to check existence of key %s in %s: %s", key, tier.value, e)

        return False

    def flush(self, namespace: str | None = None, tier: CacheTier | None = None) -> bool:
        """Flush cache with optional tier and namespace filtering."""
        success = False

        target_tiers = (
            [tier] if tier else [CacheTier.L1_MEMORY, CacheTier.L2_REDIS]
        )

        for t in target_tiers:
            if not self._get_cache_for_tier(t) or self._is_circuit_open(t):
                continue

            try:
                cache_instance = self._get_cache_for_tier(t)
                result = cache_instance.flush(namespace)

                if result:
                    success = True
                    logger.info("Flushed cache tier %s, namespace: %s", t.value, namespace or "all")

            except Exception as e:
                self._handle_circuit_breaker(t, e)
                logger.error("Failed to flush cache tier %s: %s", t.value, e)

        return success

    def get_stats(self) -> dict[str, dict[str, int | float]]:
        """Get comprehensive cache statistics."""
        stats = {}

        for tier, tier_stats in self.stats.items():
            stats[tier.value] = {
                "hits": tier_stats.hits,
                "misses": tier_stats.misses,
                "hit_rate": round(tier_stats.hit_rate, 2),
                "sets": tier_stats.sets,
                "deletes": tier_stats.deletes,
                "errors": tier_stats.errors,
                "avg_access_time_ms": round(tier_stats.avg_access_time, 2),
                "circuit_open": self._is_circuit_open(tier),
                "total_requests": tier_stats.hits + tier_stats.misses,
            }

        # Overall statistics
        total_hits = sum(s.hits for s in self.stats.values())
        total_misses = sum(s.misses for s in self.stats.values())
        total_requests = total_hits + total_misses
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0

        stats["overall"] = {
            "total_requests": total_requests,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "overall_hit_rate": round(overall_hit_rate, 2),
            "total_errors": sum(s.errors for s in self.stats.values()),
        }

        return stats

    def get_info(self) -> dict[str, Any]:
        """Get cache information and configuration."""
        info = {
            "enabled_tiers": {
                "l1_memory": self.enable_l1,
                "l2_redis": self.enable_l2,
            },
            "configuration": {"circuit_breaker_timeout": self.circuit_breaker_timeout},
            "stats": self.get_stats(),
        }

        # Add individual cache info
        if self.l1_cache:
            info["l1_info"] = self.l1_cache.info()
        if self.l2_cache:
            info["l2_info"] = self.l2_cache.info()

        return info

    def close(self):
        """Close all cache connections."""
        if self.l1_cache:
            self.l1_cache.close()
        if self.l2_cache:
            self.l2_cache.close()
        logger.info("CacheManager closed")


def get_cache_manager() -> CacheManager | None:
    """Get cache manager instance from Dependencies container."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    return deps.cache_manager if deps is not None else None
