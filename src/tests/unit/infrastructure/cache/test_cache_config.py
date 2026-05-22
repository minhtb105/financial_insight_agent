import pytest

from infrastructure.cache.config import CacheConfig, CacheTier
from infrastructure.cache.serialization import SerializationFormat


class TestCacheConfig:
    def test_default_config(self):
        cfg = CacheConfig()
        assert cfg.config["redis"]["host"] == "localhost"
        assert cfg.config["cache_tiers"]["l1_memory"]["enabled"] is True
        assert cfg.config["optimization"]["compression_enabled"] is True

    def test_custom_config_overrides_default(self):
        cfg = CacheConfig({"redis": {"host": "10.0.0.1", "port": 6380, "max_connections": 50}})
        assert cfg.config["redis"]["host"] == "10.0.0.1"
        assert cfg.config["redis"]["port"] == 6380

    def test_custom_config_preserves_defaults_for_missing_keys(self):
        cfg = CacheConfig({"redis": {"host": "10.0.0.1", "port": 6379, "max_connections": 50}})
        assert cfg.config["redis"]["host"] == "10.0.0.1"
        assert cfg.config["redis"]["port"] == 6379

    def test_get_redis_config(self):
        cfg = CacheConfig()
        assert cfg.get_redis_config()["host"] == "localhost"

    def test_get_tier_config_by_enum(self):
        cfg = CacheConfig()
        tier = cfg.get_tier_config(CacheTier.L1_MEMORY)
        assert tier["ttl_hours"] == 0.5

    def test_get_tier_config_by_string(self):
        cfg = CacheConfig()
        tier = cfg.get_tier_config("l1_memory")
        assert tier["ttl_hours"] == 0.5

    def test_get_tier_config_unknown(self):
        cfg = CacheConfig()
        assert cfg.get_tier_config("nonexistent") == {}

    def test_get_serialization_format(self):
        cfg = CacheConfig()
        fmt = cfg.get_serialization_format(CacheTier.L1_MEMORY)
        assert fmt == SerializationFormat.JSON

    def test_get_serialization_format_unknown_tier(self):
        cfg = CacheConfig()
        fmt = cfg.get_serialization_format("nonexistent")
        assert fmt == SerializationFormat.JSON

    def test_get_optimization_config(self):
        cfg = CacheConfig()
        opts = cfg.get_optimization_config()
        assert opts["compression_enabled"] is True

    def test_get_monitoring_config(self):
        cfg = CacheConfig()
        mon = cfg.get_monitoring_config()
        assert mon["enable_metrics"] is True

    def test_is_tier_enabled_true(self):
        cfg = CacheConfig()
        assert cfg.is_tier_enabled(CacheTier.L1_MEMORY) is True

    def test_is_tier_enabled_false_custom(self):
        cfg = CacheConfig(
            {
                "redis": {"port": 6379, "max_connections": 50},
                "cache_tiers": {
                    "test": {"enabled": False, "ttl_hours": 1, "serialization_format": "json"}
                },
            }
        )
        assert cfg.is_tier_enabled("test") is False

    def test_get_ttl_hours(self):
        cfg = CacheConfig()
        assert cfg.get_ttl_hours(CacheTier.L1_MEMORY) == 0.5

    def test_get_all_tiers(self):
        cfg = CacheConfig()
        tiers = cfg.get_all_tiers()
        assert "l1_memory" in tiers
        assert "l2_redis" in tiers
        assert len(tiers) == 6

    def test_get_enabled_tiers(self):
        cfg = CacheConfig()
        enabled = cfg.get_enabled_tiers()
        assert "l1_memory" in enabled
        assert isinstance(enabled, dict)

    def test_validate_valid_config(self):
        cfg = CacheConfig()
        assert cfg.config["redis"]["port"] == 6379

    def test_validate_invalid_port_type(self):
        with pytest.raises(ValueError, match="port must be integer"):
            CacheConfig({"redis": {"port": "abc"}})

    def test_validate_port_out_of_range(self):
        with pytest.raises(ValueError, match="port must be 1-65535"):
            CacheConfig({"redis": {"port": 0}})

    def test_validate_negative_max_connections(self):
        with pytest.raises(ValueError, match="Max connections must be positive"):
            CacheConfig({"redis": {"port": 6379, "max_connections": 0}})

    def test_validate_non_numeric_ttl(self):
        with pytest.raises(ValueError, match="TTL must be numeric"):
            CacheConfig(
                {
                    "redis": {"port": 6379, "max_connections": 50},
                    "cache_tiers": {"l1_memory": {"ttl_hours": "abc"}},
                }
            )

    def test_validate_negative_ttl(self):
        with pytest.raises(ValueError, match="TTL must be positive"):
            CacheConfig(
                {
                    "redis": {"port": 6379, "max_connections": 50},
                    "cache_tiers": {"l1_memory": {"ttl_hours": -1}},
                }
            )

    def test_invalid_serialization_format_uses_json(self):
        cfg = CacheConfig(
            {
                "redis": {"port": 6379, "max_connections": 50},
                "cache_tiers": {
                    "l1_memory": {
                        "ttl_hours": 1,
                        "enabled": True,
                        "serialization_format": "invalid",
                    }
                },
            }
        )
        assert cfg.get_tier_config("l1_memory")["serialization_format"] == "json"

    def test_get_performance_recommendations_default(self):
        cfg = CacheConfig()
        recs = cfg.get_performance_recommendations()
        assert "recommendations" in recs
        assert "config_summary" in recs
        assert recs["config_summary"]["total_tiers"] == 6
        assert recs["config_summary"]["compression_enabled"] is True

    def test_recommendations_flag_disabled_compression(self):
        cfg = CacheConfig(
            {
                "redis": {"port": 6379, "max_connections": 50},
                "optimization": {"compression_enabled": False},
            }
        )
        recs = cfg.get_performance_recommendations()
        rec_types = [r["type"] for r in recs["recommendations"]]
        assert "optimization" in rec_types

    def test_recommendations_flag_long_ttl(self):
        cfg = CacheConfig(
            {
                "redis": {"port": 6379, "max_connections": 50},
                "cache_tiers": {
                    f"test_{i}": {
                        "enabled": True,
                        "ttl_hours": ttl,
                        "serialization_format": "msgpack",
                    }
                    for i, ttl in enumerate([1, 100])
                },
            }
        )
        recs = cfg.get_performance_recommendations()
        rec_types = [r["type"] for r in recs["recommendations"]]
        assert "ttl" in rec_types


class TestCacheConfigGetSetInstance:
    def teardown_method(self):
        from infrastructure.cache import config as cfg_mod

        cfg_mod._cache_config_instance = None

    def test_get_cache_config_creates_default(self):
        from infrastructure.cache.config import get_cache_config

        cfg = get_cache_config()
        assert isinstance(cfg, CacheConfig)

    def test_get_cache_config_returns_same_instance(self):
        from infrastructure.cache.config import get_cache_config

        c1 = get_cache_config()
        c2 = get_cache_config()
        assert c1 is c2

    def test_set_cache_config_instance(self):
        from infrastructure.cache.config import get_cache_config, set_cache_config_instance

        custom = CacheConfig({"redis": {"host": "custom", "port": 6379, "max_connections": 50}})
        set_cache_config_instance(custom)
        assert get_cache_config().config["redis"]["host"] == "custom"
