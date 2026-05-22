"""Unit tests for CacheManager."""

from infrastructure.cache.cache_manager import CacheManager


def test_init_default():
    from infrastructure.cache.memory_cache import MemoryCache

    cm = CacheManager(enable_l1=True, enable_l2=False)
    assert isinstance(cm.l1_cache, MemoryCache)
    assert cm.l2_cache is None


def test_get_miss():
    cm = CacheManager(enable_l1=True, enable_l2=False)
    result = cm.get("nonexistent")
    assert result is None


def test_set_and_get_l1():
    cm = CacheManager(enable_l1=True, enable_l2=False)
    cm.set("key1", "value1")
    result = cm.get("key1")
    assert result == "value1"


def test_delete():
    cm = CacheManager(enable_l1=True, enable_l2=False)
    cm.set("key1", "value1")
    assert cm.delete("key1") is True
    assert cm.get("key1") is None


def test_exists():
    cm = CacheManager(enable_l1=True, enable_l2=False)
    cm.set("key1", "value1")
    assert cm.exists("key1") is True
    assert cm.exists("nope") is False


def test_flush():
    cm = CacheManager(enable_l1=True, enable_l2=False)
    cm.set("a", 1)
    cm.set("b", 2)
    cm.flush()
    assert cm.get("a") is None


def test_get_info():
    cm = CacheManager(enable_l1=True, enable_l2=False)
    info = cm.get_info()
    assert info["enabled_tiers"]["l1_memory"] is True
    assert info["enabled_tiers"]["l2_redis"] is False
    assert "l1_info" in info
    assert "configuration" in info


def test_stats():
    cm = CacheManager(enable_l1=True, enable_l2=False)
    cm.get("miss")
    stats = cm.get_stats()
    assert stats["overall"]["total_misses"] == 1
    assert stats["overall"]["total_hits"] == 0
    cm.set("exists", "val")
    cm.get("exists")
    stats = cm.get_stats()
    assert stats["overall"]["total_hits"] == 1
    assert stats["overall"]["total_misses"] == 1
