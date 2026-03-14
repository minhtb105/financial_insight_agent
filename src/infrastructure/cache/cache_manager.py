"""
Multi-tier cache manager for the financial insight agent.

Implements a hierarchical caching strategy with automatic promotion/demotion
between cache tiers based on access patterns and data importance.
"""

import logging
import time
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass
from enum import Enum

from infrastructure.cache.redis_cache import RedisCache, get_cache as get_redis_cache
from infrastructure.cache.memory_cache import MemoryCache

logger = logging.getLogger(__name__)


class CacheTier(Enum):
    """Cache tier levels."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DATABASE = "l3_database"


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
        return (self.total_access_time / (self.hits + self.misses) * 1000) if (self.hits + self.misses) > 0 else 0.0


class CacheManager:
    """
    Multi-tier cache manager with intelligent data placement and migration.
    
    Features:
    - L1: In-memory cache (fastest, volatile)
    - L2: Redis cache (fast, persistent)
    - L3: Database cache (slow, persistent)
    - Automatic promotion/demotion based on access patterns
    - Circuit breaker for failed tiers
    - Metrics collection and monitoring
    """
    
    def __init__(
        self,
        enable_l1: bool = True,
        enable_l2: bool = True,
        enable_l3: bool = False,  # Database tier not implemented yet
        l1_max_size: int = 500,
        l1_ttl_hours: int = 0.5,  # 30 minutes
        l2_ttl_hours: int = 2,
        promotion_threshold: int = 3,  # Access count to promote to L1
        demotion_threshold_hours: int = 1,  # Hours since last access to demote from L1
        circuit_breaker_timeout: int = 30  # Seconds
    ):
        """
        Initialize multi-tier cache manager.
        
        Args:
            enable_l1: Enable L1 memory cache
            enable_l2: Enable L2 Redis cache
            enable_l3: Enable L3 database cache
            l1_max_size: L1 cache max size
            l1_ttl_hours: L1 cache default TTL
            l2_ttl_hours: L2 cache default TTL
            promotion_threshold: Access count to promote to L1
            demotion_threshold_hours: Hours since last access to demote from L1
            circuit_breaker_timeout: Circuit breaker timeout in seconds
        """
        self.enable_l1 = enable_l1
        self.enable_l2 = enable_l2
        self.enable_l3 = enable_l3
        
        self.promotion_threshold = promotion_threshold
        self.demotion_threshold = demotion_threshold_hours * 3600  # Convert to seconds
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
        # Initialize cache tiers
        self.l1_cache = MemoryCache(max_size=l1_max_size, default_ttl_hours=l1_ttl_hours) if enable_l1 else None
        self.l2_cache = RedisCache(ttl_hours=l2_ttl_hours) if enable_l2 else None
        
        # Statistics
        self.stats = {
            CacheTier.L1_MEMORY: CacheStats(CacheTier.L1_MEMORY),
            CacheTier.L2_REDIS: CacheStats(CacheTier.L2_REDIS),
            CacheTier.L3_DATABASE: CacheStats(CacheTier.L3_DATABASE)
        }
        
        # Circuit breaker states
        self.circuit_states = {
            CacheTier.L1_MEMORY: {"open": False, "last_failure": 0},
            CacheTier.L2_REDIS: {"open": False, "last_failure": 0},
            CacheTier.L3_DATABASE: {"open": False, "last_failure": 0}
        }
        
        logger.info(f"Initialized CacheManager with tiers: L1={enable_l1}, L2={enable_l2}, L3={enable_l3}")
    
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
        state = self.circuit_states[tier]
        if not state["open"]:
            return False
        
        if time.time() - state["last_failure"] > self.circuit_breaker_timeout:
            # Circuit breaker timeout expired, close it
            state["open"] = False
            logger.info(f"Circuit breaker closed for {tier.value}")
            return False
        
        return True
    
    def _record_access(self, tier: CacheTier, operation: str, duration: float, success: bool = True):
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
        elif not success:
            stats.errors += 1
        
        stats.total_access_time += duration
    
    def _promote_to_l1(self, key: str, value: Any, namespace: str):
        """Promote item from L2 to L1 based on access patterns."""
        if not self.enable_l1 or not self.l1_cache:
            return
        
        try:
            # Check if L1 has space or can evict
            if len(self.l1_cache._cache) >= self.l1_cache.max_size:
                # L1 is full, check for items to demote
                self._demote_l1_items()
            
            # Promote to L1
            self.l1_cache.set(key, value, namespace=namespace)
            logger.debug(f"Promoted key {key} to L1 cache")
            
        except Exception as e:
            logger.error(f"Failed to promote key {key} to L1: {e}")
    
    def _demote_l1_items(self):
        """Demote least recently used items from L1 to L2."""
        if not self.enable_l2 or not self.l2_cache:
            return
        
        try:
            # Get items sorted by last access time
            l1_items = list(self.l1_cache._access_order.items())
            l1_items.sort(key=lambda x: x[1])  # Sort by access time (oldest first)
            
            # Demote half of the items
            items_to_demote = l1_items[:len(l1_items) // 2]
            
            for key, _ in items_to_demote:
                try:
                    # Get value from L1
                    value = self.l1_cache.get(key.split(":", 1)[1], namespace=key.split(":", 1)[0])
                    if value:
                        # Store in L2 with longer TTL
                        self.l2_cache.set(key, value, ttl_hours=2)
                    
                    # Remove from L1
                    self.l1_cache.delete(key.split(":", 1)[1], namespace=key.split(":", 1)[0])
                    
                except Exception as e:
                    logger.error(f"Failed to demote key {key} from L1 to L2: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to demote L1 items: {e}")
    
    def get(self, key: str, namespace: str = "cache") -> Optional[Any]:
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
                    logger.debug(f"L1 cache hit for key {key}")
                    return value
                else:
                    self._record_access(CacheTier.L1_MEMORY, "get", duration, success=False)
                    
            except Exception as e:
                self._record_access(CacheTier.L1_MEMORY, "get", duration, success=False)
                self._handle_circuit_breaker(CacheTier.L1_MEMORY, e)
                logger.warning(f"L1 cache error for key {key}: {e}")
        
        # Try L2 (if enabled and circuit not open)
        if self.enable_l2 and self.l2_cache and not self._is_circuit_open(CacheTier.L2_REDIS):
            try:
                value = self.l2_cache.get(key, namespace)
                duration = time.time() - start_time
                
                if value is not None:
                    self._record_access(CacheTier.L2_REDIS, "get", duration, success=True)
                    logger.debug(f"L2 cache hit for key {key}")
                    
                    # Promote to L1 if enabled
                    if self.enable_l1:
                        self._promote_to_l1(key, value, namespace)
                    
                    return value
                else:
                    self._record_access(CacheTier.L2_REDIS, "get", duration, success=False)
                    
            except Exception as e:
                self._record_access(CacheTier.L2_REDIS, "get", duration, success=False)
                self._handle_circuit_breaker(CacheTier.L2_REDIS, e)
                logger.warning(f"L2 cache error for key {key}: {e}")
        
        # Try L3 (if enabled and circuit not open)
        if self.enable_l3 and not self._is_circuit_open(CacheTier.L3_DATABASE):
            try:
                # TODO: Implement L3 database cache
                duration = time.time() - start_time
                self._record_access(CacheTier.L3_DATABASE, "get", duration, success=False)
                
            except Exception as e:
                duration = time.time() - start_time
                self._record_access(CacheTier.L3_DATABASE, "get", duration, success=False)
                self._handle_circuit_breaker(CacheTier.L3_DATABASE, e)
                logger.warning(f"L3 cache error for key {key}: {e}")
        
        # Cache miss
        total_duration = time.time() - start_time
        logger.debug(f"Cache miss for key {key} (total duration: {total_duration:.3f}s)")
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_hours: Optional[int] = None,
        namespace: str = "cache",
        force_tier: Optional[CacheTier] = None
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
            if self.enable_l3:
                target_tiers.append(CacheTier.L3_DATABASE)
        
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
                    logger.debug(f"Successfully set key {key} in {tier.value}")
                else:
                    self._record_access(tier, "set", duration, success=False)
                    
            except Exception as e:
                duration = time.time() - start_time
                self._record_access(tier, "set", duration, success=False)
                self._handle_circuit_breaker(tier, e)
                logger.error(f"Failed to set key {key} in {tier.value}: {e}")
        
        return success
    
    def delete(self, key: str, namespace: str = "cache") -> bool:
        """Delete key from all cache tiers."""
        success = False
        
        for tier in [CacheTier.L1_MEMORY, CacheTier.L2_REDIS, CacheTier.L3_DATABASE]:
            if not self._get_cache_for_tier(tier) or self._is_circuit_open(tier):
                continue
            
            try:
                cache_instance = self._get_cache_for_tier(tier)
                result = cache_instance.delete(key, namespace)
                
                if result:
                    self._record_access(tier, "delete", 0, success=True)
                    success = True
                    logger.debug(f"Deleted key {key} from {tier.value}")
                    
            except Exception as e:
                self._record_access(tier, "delete", 0, success=False)
                self._handle_circuit_breaker(tier, e)
                logger.error(f"Failed to delete key {key} from {tier.value}: {e}")
        
        return success
    
    def _handle_circuit_breaker(self, tier: CacheTier, error: Exception):
        """Handle circuit breaker logic for failed cache tier."""
        state = self.circuit_states[tier]
        state["open"] = True
        state["last_failure"] = time.time()
        
        logger.warning(f"Circuit breaker opened for {tier.value} due to error: {error}")
    
    def exists(self, key: str, namespace: str = "cache") -> bool:
        """Check if key exists in any cache tier."""
        for tier in [CacheTier.L1_MEMORY, CacheTier.L2_REDIS, CacheTier.L3_DATABASE]:
            if not self._get_cache_for_tier(tier) or self._is_circuit_open(tier):
                continue
            
            try:
                cache_instance = self._get_cache_for_tier(tier)
                if cache_instance.exists(key, namespace):
                    return True
                    
            except Exception as e:
                self._handle_circuit_breaker(tier, e)
                logger.error(f"Failed to check existence of key {key} in {tier.value}: {e}")
        
        return False
    
    def flush(self, namespace: Optional[str] = None, tier: Optional[CacheTier] = None) -> bool:
        """Flush cache with optional tier and namespace filtering."""
        success = False
        
        target_tiers = [tier] if tier else [CacheTier.L1_MEMORY, CacheTier.L2_REDIS, CacheTier.L3_DATABASE]
        
        for tier in target_tiers:
            if not self._get_cache_for_tier(tier) or self._is_circuit_open(tier):
                continue
            
            try:
                cache_instance = self._get_cache_for_tier(tier)
                result = cache_instance.flush(namespace)
                
                if result:
                    success = True
                    logger.info(f"Flushed cache tier {tier.value}, namespace: {namespace or 'all'}")
                    
            except Exception as e:
                self._handle_circuit_breaker(tier, e)
                logger.error(f"Failed to flush cache tier {tier.value}: {e}")
        
        return success
    
    def get_stats(self) -> Dict[str, Dict[str, Union[int, float]]]:
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
                "total_requests": tier_stats.hits + tier_stats.misses
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
            "total_errors": sum(s.errors for s in self.stats.values())
        }
        
        return stats
    
    def get_info(self) -> Dict[str, Any]:
        """Get cache information and configuration."""
        info = {
            "enabled_tiers": {
                "l1_memory": self.enable_l1,
                "l2_redis": self.enable_l2,
                "l3_database": self.enable_l3
            },
            "configuration": {
                "promotion_threshold": self.promotion_threshold,
                "demotion_threshold_hours": self.demotion_threshold / 3600,
                "circuit_breaker_timeout": self.circuit_breaker_timeout
            },
            "stats": self.get_stats()
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


# Global cache manager instance
_cache_manager_instance: Optional[CacheManager] = None


def get_cache_manager() -> Optional[CacheManager]:
    """Get global cache manager instance."""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        try:
            _cache_manager_instance = CacheManager()
        except Exception as e:
            logger.error(f"Failed to create cache manager instance: {e}")
            _cache_manager_instance = None
    return _cache_manager_instance


def set_cache_manager_instance(manager: CacheManager) -> None:
    """Set global cache manager instance (for testing)."""
    global _cache_manager_instance
    _cache_manager_instance = manager