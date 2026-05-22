"""Unit tests for MemoryCache."""

import time
from infrastructure.cache.memory_cache import MemoryCache


def test_set_and_get():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    cache.set("key1", {"data": 123})
    result = cache.get("key1")
    assert result == {"data": 123}


def test_get_missing():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    assert cache.get("nonexistent") is None


def test_delete():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    cache.set("key1", "value1")
    assert cache.delete("key1") is True
    assert cache.get("key1") is None


def test_delete_missing():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    assert cache.delete("nonexistent") is False


def test_exists():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    cache.set("key1", "value1")
    assert cache.exists("key1") is True
    assert cache.exists("nonexistent") is False


def test_flush():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.flush()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_flush_namespace():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    cache.set("key1", "val1", namespace="ns1")
    cache.set("key2", "val2", namespace="ns2")
    cache.flush(namespace="ns1")
    assert cache.get("key1", namespace="ns1") is None
    assert cache.get("key2", namespace="ns2") == "val2"


def test_ttl_expiry():
    cache = MemoryCache(max_size=10, default_ttl_hours=0)
    cache.set("expires_soon", "value")
    time.sleep(0.01)
    assert cache.get("expires_soon") is None
    assert cache.exists("expires_soon") is False


def test_lru_eviction():
    cache = MemoryCache(max_size=6, default_ttl_hours=1)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)
    cache.set("e", 5)
    cache.set("f", 6)
    cache.set("g", 7)
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("c") is not None
    assert cache.get("d") is not None
    assert cache.get("e") is not None
    assert cache.get("f") is not None
    assert cache.get("g") is not None


def test_lru_recently_used_preserved():
    cache = MemoryCache(max_size=6, default_ttl_hours=1)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)
    cache.set("e", 5)
    cache.get("a")
    cache.set("f", 6)
    cache.set("g", 7)
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_info():
    cache = MemoryCache(max_size=10, default_ttl_hours=1)
    info = cache.info()
    assert info["cache_type"] == "memory"
    assert info["max_size"] == 10
    assert info["current_size"] == 0
    assert info["default_ttl_hours"] == 1
