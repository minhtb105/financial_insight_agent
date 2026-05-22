"""Unit tests for RedisCache (with mocked Redis)."""

from unittest.mock import MagicMock, patch
import pytest

from redis.exceptions import RedisError

from infrastructure.cache.redis_cache import RedisCache
from infrastructure.cache.serialization import SerializationFormat


@pytest.fixture
def cache(mock_redis_client):
    with patch("infrastructure.cache.redis_cache.redis.Redis", return_value=mock_redis_client):
        c = RedisCache(host="localhost", port=6379)
    yield c
    c.close()


# -- Init / connection ----------------------------------------------------


def test_init_creates_client(mock_redis_client):
    with patch("infrastructure.cache.redis_cache.redis.Redis", return_value=mock_redis_client):
        c = RedisCache(host="localhost", port=6379)
    assert c._client is not None
    mock_redis_client.ping.assert_called_once()
    c.close()


def test_init_connection_failure():
    mock_fail = MagicMock()
    mock_fail.ping.side_effect = RedisError("No connection")
    with patch("infrastructure.cache.redis_cache.redis.Redis", return_value=mock_fail) as mr:
        c = RedisCache(host="localhost", port=6379)
    assert c._client is None
    c.close()


# -- get_raw_client -------------------------------------------------------


def test_get_raw_client_returns_none_when_disconnected():
    cache = _make_dead_cache()
    assert cache.get_raw_client() is None


# -- set / get (JSON) -----------------------------------------------------


def test_set_and_get(cache, mock_redis_client):
    mock_redis_client.setex.return_value = True
    mock_redis_client.get.return_value = '"value1"'
    assert cache.set("key1", "value1") is True
    result = cache.get("key1")
    assert result == "value1"


def test_get_returns_none_on_miss(cache, mock_redis_client):
    mock_redis_client.get.return_value = None
    assert cache.get("missing") is None


def test_get_returns_none_on_redis_error(cache, mock_redis_client):
    mock_redis_client.get.side_effect = RedisError()
    assert cache.get("key") is None


def test_set_returns_false_on_redis_error(cache, mock_redis_client):
    mock_redis_client.setex.side_effect = RedisError()
    assert cache.set("key", "val") is False


# -- set / get (REDIS_HASH) -----------------------------------------------


def test_set_redis_hash(cache, mock_redis_client):
    mock_redis_client.hset.return_value = 1
    mock_redis_client.expire.return_value = True
    result = cache.set(
        "hash_key",
        {"name": "VCB", "price": "100"},
        format=SerializationFormat.REDIS_HASH,
    )
    assert result is True
    mock_redis_client.hset.assert_called_once()
    mock_redis_client.expire.assert_called_once()


def test_get_redis_hash(cache, mock_redis_client):
    mock_redis_client.hgetall.return_value = {"name": "VCB", "price": "100"}
    result = cache.get("hash_key", format=SerializationFormat.REDIS_HASH)
    assert result == {"name": "VCB", "price": "100"}


# -- delete / exists ------------------------------------------------------


def test_delete(cache, mock_redis_client):
    mock_redis_client.delete.return_value = 1
    assert cache.delete("key1") is True


def test_delete_not_found(cache, mock_redis_client):
    mock_redis_client.delete.return_value = 0
    assert cache.delete("nonexistent") is False


def test_exists_true(cache, mock_redis_client):
    mock_redis_client.exists.return_value = 1
    assert cache.exists("existing") is True


def test_exists_false(cache, mock_redis_client):
    mock_redis_client.exists.return_value = 0
    assert cache.exists("missing") is False


# -- keys (SCAN-based) ----------------------------------------------------


def test_keys(cache, mock_redis_client):
    mock_redis_client.scan_iter.return_value = ["cache:k1", "cache:k2"]
    result = cache.keys("*")
    assert result == ["k1", "k2"]


def test_keys_empty(cache, mock_redis_client):
    mock_redis_client.scan_iter.return_value = []
    assert cache.keys("*") == []


# -- flush ----------------------------------------------------------------


def test_flush_namespace(cache, mock_redis_client):
    mock_redis_client.scan_iter.return_value = ["cache:k1", "cache:k2"]
    mock_redis_client.delete.return_value = 2
    assert cache.flush(namespace="cache") is True


def test_flush_all(cache, mock_redis_client):
    mock_redis_client.flushdb.return_value = True
    assert cache.flush() is True


# -- list operations ------------------------------------------------------


def test_list_push(cache, mock_redis_client):
    mock_redis_client.lpush.return_value = 1
    assert cache.list_push("mylist", "item1") is True


def test_list_range(cache, mock_redis_client):
    mock_redis_client.lrange.return_value = ["a", "b"]
    assert cache.list_range("mylist", 0, -1) == ["a", "b"]


def test_list_length(cache, mock_redis_client):
    mock_redis_client.llen.return_value = 3
    assert cache.list_length("mylist") == 3


# -- hash operations ------------------------------------------------------


def test_hash_set(cache, mock_redis_client):
    mock_redis_client.hset.return_value = 1
    assert cache.hash_set("hk", "field1", "val1") is True


def test_hash_get_all(cache, mock_redis_client):
    mock_redis_client.hgetall.return_value = {"a": "1", "b": "2"}
    assert cache.hash_get_all("hk") == {"a": "1", "b": "2"}


def test_hash_multi_get(cache, mock_redis_client):
    mock_redis_client.hmget.return_value = ["v1", None]
    assert cache.hash_multi_get("hk", ["f1", "f2"]) == ["v1", None]


def test_hash_length(cache, mock_redis_client):
    mock_redis_client.hlen.return_value = 2
    assert cache.hash_length("hk") == 2


# -- set operations -------------------------------------------------------


def test_set_add(cache, mock_redis_client):
    mock_redis_client.sadd.return_value = 1
    assert cache.set_add("sk", "member1") is True


def test_set_members(cache, mock_redis_client):
    mock_redis_client.smembers.return_value = {"a", "b"}
    assert cache.set_members("sk") == {"a", "b"}


# -- info -----------------------------------------------------------------


def test_info(mock_redis_client):
    with patch("infrastructure.cache.redis_cache.redis.Redis", return_value=mock_redis_client):
        c = RedisCache(host="localhost", port=6379)
    mock_redis_client.info.return_value = {"redis_version": "7.0"}
    info = c.info()
    assert info["connection_status"] == "connected"
    assert "redis_info" in info
    c.close()


# -- client-down guards ---------------------------------------------------

import time as _time


def _make_dead_cache():
    cache = RedisCache.__new__(RedisCache)
    cache._client = None
    cache._last_reconnect_attempt = _time.time()
    cache._reconnect_interval = 30.0
    cache.host = "localhost"
    cache.port = 6379
    cache.db = 0
    cache.password = None
    cache.max_connections = 50
    cache.ttl_hours = 2
    cache.serialization_format = SerializationFormat.JSON
    return cache


def test_set_returns_false_when_client_none():
    cache = _make_dead_cache()
    assert cache.set("key", "value") is False


def test_get_returns_none_when_client_none():
    cache = _make_dead_cache()
    assert cache.get("key") is None


def test_delete_returns_false_when_client_none():
    cache = _make_dead_cache()
    assert cache.delete("key") is False


def test_exists_returns_false_when_client_none():
    cache = _make_dead_cache()
    assert cache.exists("key") is False


def test_info_returns_error_when_disconnected():
    cache = _make_dead_cache()
    info = cache.info()
    assert "error" in info


def test_get_raw_client_null_when_disconnected():
    cache = _make_dead_cache()
    assert cache.get_raw_client() is None
