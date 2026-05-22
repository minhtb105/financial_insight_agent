"""
Cache infrastructure package for the financial insight agent.

Provides multi-tier caching with Redis Hash, MessagePack, and JSON serialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cache_manager import CacheManager
    from .redis_cache import RedisCache
    from .session_manager import SessionManager


__all__ = [
    # Core cache classes
    "CacheConfig",
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    "SerializationFormat",
    "SerializationManager",
    "SessionManager",
    # Global instances
    "get_cache",
    # Configuration
    "get_cache_config",
    "get_cache_manager",
    "get_cache_with_format",
    "get_memory_cache",
    "get_serialization_manager",
    "get_session_manager",
    # Instance setters (for testing)
    "set_cache_config_instance",
    "set_cache_instance",
    "set_cache_manager_instance",
    "set_memory_cache_instance",
    "set_serialization_manager_instance",
    "set_session_manager_instance",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "RedisCache": ".redis_cache",
        "MemoryCache": ".memory_cache",
        "CacheManager": ".cache_manager",
        "SessionManager": ".session_manager",
        "SerializationManager": ".serialization",
        "SerializationFormat": ".serialization",
        "CacheConfig": ".config",
        "get_cache": ".redis_cache",
        "get_cache_with_format": ".redis_cache",
        "get_memory_cache": ".memory_cache",
        "get_cache_manager": ".cache_manager",
        "get_session_manager": ".session_manager",
        "get_serialization_manager": ".serialization",
        "get_cache_config": ".config",
        "set_cache_instance": ".redis_cache",
        "set_memory_cache_instance": ".memory_cache",
        "set_cache_manager_instance": ".cache_manager",
        "set_session_manager_instance": ".session_manager",
        "set_serialization_manager_instance": ".serialization",
        "set_cache_config_instance": ".config",
        "make_cache_key": ".cache_keys",
        "make_overview_cache_key": ".cache_keys",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

