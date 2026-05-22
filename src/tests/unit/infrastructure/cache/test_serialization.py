"""Unit tests for SerializationManager — all serialization formats."""

import json
from infrastructure.cache.serialization import (
    SerializationManager,
    SerializationFormat,
)


def _make_mgr(fmt=SerializationFormat.JSON):
    return SerializationManager(default_format=fmt)


# -- JSON format ---------------------------------------------------------


def test_serialize_json_dict():
    mgr = _make_mgr()
    data = {"key": "value", "num": 42}
    serialized = mgr.serialize(data, SerializationFormat.JSON)
    assert json.loads(serialized) == data


def test_serialize_json_list():
    mgr = _make_mgr()
    serialized = mgr.serialize([1, 2, 3], SerializationFormat.JSON)
    assert json.loads(serialized) == [1, 2, 3]


def test_serialize_json_non_serializable():
    mgr = _make_mgr()

    class Foo:
        def __str__(self):
            return "foo"

    serialized = mgr.serialize(Foo(), SerializationFormat.JSON)
    assert "foo" in serialized


def test_deserialize_json():
    mgr = _make_mgr()
    result = mgr.deserialize('{"a": 1}', SerializationFormat.JSON)
    assert result == {"a": 1}


def test_deserialize_json_invalid():
    mgr = _make_mgr()
    import pytest

    with pytest.raises(json.JSONDecodeError):
        mgr.deserialize("not json", SerializationFormat.JSON)


# -- Redis Hash format ---------------------------------------------------


def test_serialize_redis_hash_dict():
    mgr = _make_mgr()
    data = {"name": "VCB", "price": 100}
    result = mgr.serialize(data, SerializationFormat.REDIS_HASH)
    assert result == {"name": "VCB", "price": "100"}


def test_serialize_redis_hash_nested():
    mgr = _make_mgr()
    data = {"name": "VCB", "nested": {"a": 1}}
    result = mgr.serialize(data, SerializationFormat.REDIS_HASH)
    assert result["name"] == "VCB"
    assert json.loads(result["nested"]) == {"a": 1}


def test_serialize_redis_hash_non_dict():
    mgr = _make_mgr()
    result = mgr.serialize("hello", SerializationFormat.REDIS_HASH)
    assert result["value"] == "hello"


def test_deserialize_redis_hash():
    mgr = _make_mgr()
    data = {"name": "VCB", "nested": '{"a": 1}'}
    result = mgr.deserialize(data, SerializationFormat.REDIS_HASH)
    assert result["name"] == "VCB"
    assert result["nested"] == {"a": 1}


def test_deserialize_redis_hash_non_dict():
    mgr = _make_mgr()
    result = mgr.deserialize("plain string", SerializationFormat.REDIS_HASH)
    assert result == "plain string"


# -- Auto-detect format --------------------------------------------------


def test_detect_redis_hash():
    mgr = _make_mgr()
    assert mgr._detect_format({"a": "1"}) == SerializationFormat.REDIS_HASH


def test_detect_json():
    mgr = _make_mgr()
    assert mgr._detect_format('{"a": 1}') == SerializationFormat.JSON


# -- Default format ------------------------------------------------------


def test_default_format():
    mgr = _make_mgr(SerializationFormat.JSON)
    result = mgr.serialize({"a": 1})
    assert isinstance(result, str)


# -- get_compression_ratio -----------------------------------------------


def test_compression_ratio_json():
    mgr = _make_mgr()
    ratio = mgr.get_compression_ratio({"a": 1}, SerializationFormat.JSON)
    assert ratio == 1.0


# -- get_format_stats ----------------------------------------------------


def test_format_stats():
    mgr = _make_mgr()
    stats = mgr.get_format_stats({"a": 1})
    assert "json" in stats
    assert stats["json"]["compression"] == 1.0
    assert stats["json"]["size"] > 0
