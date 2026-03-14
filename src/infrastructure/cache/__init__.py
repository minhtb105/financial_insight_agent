"""
Cache infrastructure package for the financial insight agent.

Provides multi-tier caching with Redis Hash, MessagePack, and JSON serialization.
"""

from .redis_cache import RedisCache, get_cache, get_cache_with_format, set_cache_instance
from .memory_cache import MemoryCache, get_memory_cache, set_memory_cache_instance
from .cache_manager import CacheManager, get_cache_manager, set_cache_manager_instance
from .session_manager import SessionManager, get_session_manager, set_session_manager_instance
from .serialization import SerializationManager, SerializationFormat, get_serialization_manager, set_serialization_manager_instance
from .config import CacheConfig, get_cache_config, set_cache_config_instance
from typing import Optional, Union, Dict, Any


__all__ = [
    # Core cache classes
    'RedisCache',
    'MemoryCache', 
    'CacheManager',
    'SessionManager',
    
    # Serialization
    'SerializationManager',
    'SerializationFormat',
    
    # Configuration
    'CacheConfig',
    
    # Global instances
    'get_cache',
    'get_cache_with_format',
    'get_memory_cache',
    'get_cache_manager',
    'get_session_manager',
    'get_serialization_manager',
    'get_cache_config',
    
    # Instance setters (for testing)
    'set_cache_instance',
    'set_memory_cache_instance',
    'set_cache_manager_instance',
    'set_session_manager_instance',
    'set_serialization_manager_instance',
    'set_cache_config_instance'
]


# Convenience functions for common operations
def get_optimized_cache(tier: str = "l2_redis") -> Optional[RedisCache]:
    """
    Get optimized cache instance for specific tier.
    
    Args:
        tier: Cache tier name (l1_memory, l2_redis, session, etc.)
        
    Returns:
        Optimized cache instance or None if not available
    """
    from .config import CacheConfig, CacheTier
    from .redis_cache import get_cache_with_format
    
    config = CacheConfig()
    if not config.is_tier_enabled(tier):
        return None
    
    format_type = config.get_serialization_format(tier)
    return get_cache_with_format(format_type)


def get_session_cache() -> Optional[SessionManager]:
    """Get session cache manager with Redis Hash optimization."""
    return get_session_manager()


def get_memory_cache_optimized() -> Optional[CacheManager]:
    """Get optimized memory cache manager with MessagePack."""
    return get_cache_manager()


def get_compression_stats(data: Any) -> Dict[str, Dict[str, Union[int, float]]]:
    """
    Get compression statistics for different serialization formats.
    
    Args:
        data: Data to analyze
        
    Returns:
        Dictionary with compression statistics
    """
    from .serialization import get_serialization_manager
    
    manager = get_serialization_manager()
    return manager.get_format_stats(data)


def get_cache_recommendations() -> Dict[str, Any]:
    """Get cache optimization recommendations."""
    from .config import get_cache_config
    
    config = get_cache_config()
    return config.get_performance_recommendations()