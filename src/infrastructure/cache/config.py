"""
Configuration system for Redis caching with multiple serialization formats.

Provides centralized configuration management for cache settings, serialization
formats, and performance optimization.
"""

import logging
from typing import Optional, Dict, Any, Union
from enum import Enum

from infrastructure.cache.serialization import SerializationFormat

logger = logging.getLogger(__name__)


class CacheTier(Enum):
    """Cache tier identifiers."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DATABASE = "l3_database"
    SESSION = "session"
    SHORT_TERM_MEMORY = "short_term_memory"
    EPISODIC_MEMORY = "episodic_memory"
    LONG_TERM_MEMORY = "long_term_memory"


class CacheConfig:
    """Configuration for cache settings and optimization."""
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        Initialize cache configuration.
        
        Args:
            config_data: Configuration dictionary
        """
        self.config = config_data or self._get_default_config()
        self._validate_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default cache configuration."""
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "password": None,
                "max_connections": 50,
                "socket_timeout": 5,
                "socket_connect_timeout": 5
            },
            "cache_tiers": {
                "l1_memory": {
                    "enabled": True,
                    "max_size": 500,
                    "ttl_hours": 0.5,
                    "serialization_format": "json"
                },
                "l2_redis": {
                    "enabled": True,
                    "ttl_hours": 2,
                    "serialization_format": "json"
                },
                "session": {
                    "enabled": True,
                    "ttl_hours": 24,
                    "serialization_format": "redis_hash",
                    "cleanup_interval_hours": 6
                },
                "short_term_memory": {
                    "enabled": True,
                    "ttl_hours": 2,
                    "max_messages": 100,
                    "migration_threshold": 50,
                    "serialization_format": "msgpack"
                },
                "episodic_memory": {
                    "enabled": True,
                    "ttl_hours": 24,
                    "max_episodes": 10000,
                    "similarity_threshold": 0.7,
                    "serialization_format": "msgpack"
                },
                "long_term_memory": {
                    "enabled": True,
                    "ttl_hours": 8760,  # 1 year
                    "max_company_profiles": 1000,
                    "max_market_patterns": 500,
                    "temporal_decay_rate": 0.1,
                    "serialization_format": "redis_hash"
                }
            },
            "optimization": {
                "compression_enabled": True,
                "compression_threshold_kb": 1,
                "batch_operations_enabled": True,
                "batch_size": 100,
                "metrics_enabled": True,
                "auto_cleanup_enabled": True,
                "migration_enabled": True
            },
            "monitoring": {
                "enable_metrics": True,
                "metrics_interval_seconds": 60,
                "alert_thresholds": {
                    "hit_rate_min": 70.0,
                    "memory_usage_max_mb": 500.0,
                    "response_time_max_ms": 100.0
                }
            }
        }
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        try:
            # Validate Redis settings
            redis_config = self.config.get("redis", {})
            assert isinstance(redis_config.get("port"), int), "Redis port must be integer"
            assert 1 <= redis_config.get("port") <= 65535, "Redis port must be 1-65535"
            assert isinstance(redis_config.get("max_connections"), int), "Max connections must be integer"
            assert redis_config.get("max_connections") > 0, "Max connections must be positive"
            
            # Validate cache tier settings
            cache_tiers = self.config.get("cache_tiers", {})
            for tier_name, tier_config in cache_tiers.items():
                assert isinstance(tier_config.get("ttl_hours"), (int, float)), f"{tier_name} TTL must be numeric"
                assert tier_config.get("ttl_hours") > 0, f"{tier_name} TTL must be positive"
                
                # Validate serialization format
                format_str = tier_config.get("serialization_format", "json")
                try:
                    SerializationFormat(format_str)
                except ValueError:
                    logger.warning(f"Invalid serialization format for {tier_name}: {format_str}, using json")
                    tier_config["serialization_format"] = "json"
            
            logger.info("Cache configuration validated successfully")
            
        except AssertionError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis connection configuration."""
        return self.config.get("redis", {})
    
    def get_tier_config(self, tier: Union[CacheTier, str]) -> Dict[str, Any]:
        """Get configuration for specific cache tier."""
        tier_name = tier.value if isinstance(tier, CacheTier) else tier
        return self.config.get("cache_tiers", {}).get(tier_name, {})
    
    def get_serialization_format(self, tier: Union[CacheTier, str]) -> SerializationFormat:
        """Get serialization format for cache tier."""
        tier_config = self.get_tier_config(tier)
        format_str = tier_config.get("serialization_format", "json")
        return SerializationFormat(format_str)
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """Get optimization configuration."""
        return self.config.get("optimization", {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration."""
        return self.config.get("monitoring", {})
    
    def is_tier_enabled(self, tier: Union[CacheTier, str]) -> bool:
        """Check if cache tier is enabled."""
        tier_config = self.get_tier_config(tier)
        return tier_config.get("enabled", False)
    
    def get_ttl_hours(self, tier: Union[CacheTier, str]) -> float:
        """Get TTL in hours for cache tier."""
        tier_config = self.get_tier_config(tier)
        return tier_config.get("ttl_hours", 2.0)
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        self._deep_update(self.config, updates)
        self._validate_config()
        logger.info("Cache configuration updated")
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep update dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def get_all_tiers(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for all cache tiers."""
        return self.config.get("cache_tiers", {})
    
    def get_enabled_tiers(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for enabled cache tiers only."""
        return {
            tier_name: config 
            for tier_name, config in self.get_all_tiers().items() 
            if config.get("enabled", False)
        }
    
    def get_performance_recommendations(self) -> Dict[str, Any]:
        """Get performance optimization recommendations based on current config."""
        recommendations = []
        config = self.config
        
        # Check if compression is enabled for large objects
        if not config.get("optimization", {}).get("compression_enabled", False):
            recommendations.append({
                "type": "optimization",
                "priority": "medium",
                "message": "Consider enabling compression for large cache objects"
            })
        
        # Check serialization formats
        cache_tiers = config.get("cache_tiers", {})
        for tier_name, tier_config in cache_tiers.items():
            if tier_config.get("enabled", False):
                format_str = tier_config.get("serialization_format", "json")
                if format_str == "json":
                    recommendations.append({
                        "type": "serialization",
                        "priority": "low",
                        "message": f"Consider using MessagePack for {tier_name} to reduce memory usage"
                    })
        
        # Check TTL settings
        for tier_name, tier_config in cache_tiers.items():
            if tier_config.get("enabled", False):
                ttl = tier_config.get("ttl_hours", 2.0)
                if ttl > 24:
                    recommendations.append({
                        "type": "ttl",
                        "priority": "medium",
                        "message": f"Consider reviewing TTL for {tier_name} (currently {ttl} hours)"
                    })
        
        return {
            "recommendations": recommendations,
            "config_summary": {
                "total_tiers": len(cache_tiers),
                "enabled_tiers": len([t for t in cache_tiers.values() if t.get("enabled", False)]),
                "compression_enabled": config.get("optimization", {}).get("compression_enabled", False),
                "metrics_enabled": config.get("monitoring", {}).get("enable_metrics", False)
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.config.copy()
    
    def save_to_file(self, filepath: str) -> bool:
        """Save configuration to JSON file."""
        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {filepath}: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'CacheConfig':
        """Load configuration from JSON file."""
        try:
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            logger.info(f"Configuration loaded from {filepath}")
            return cls(config_data)
        except Exception as e:
            logger.error(f"Failed to load configuration from {filepath}: {e}")
            return cls()  # Return default config on failure


# Global configuration instance
_cache_config_instance: Optional[CacheConfig] = None


def get_cache_config() -> CacheConfig:
    """Get global cache configuration instance."""
    global _cache_config_instance
    if _cache_config_instance is None:
        _cache_config_instance = CacheConfig()
    return _cache_config_instance


def set_cache_config_instance(config: CacheConfig) -> None:
    """Set global cache configuration instance (for testing)."""
    global _cache_config_instance
    _cache_config_instance = config