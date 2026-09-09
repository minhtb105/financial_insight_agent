"""Unit tests for Working Memory + Sliding Window + Summary (FakeRedis, no infra)."""

import json

import pytest

from infrastructure.memory.short_term.memory import (
    DEFAULT_WINDOW_SIZE,
    ShortTermMemory,
)


class FakeRedis:
    """Minimal in-memory stub of the RedisCache surface used by ShortTermMemory."""

    def __init__(self):
        self.lists: dict[str, list] = {}
        self.hashes: dict[str, dict] = {}

    # -- serialization (json instead of msgpack; shape is identical) --
    def _serialize(self, item):
        return json.dumps(item)

    def _deserialize(self, data):
        return json.loads(data)

    # -- lists (LPUSH semantics: index 0 is newest) --
    def list_push(self, key, value, namespace="cache"):
        self.lists.setdefault(key, []).insert(0, value)
        return True

    def list_trim(self, key, start, stop, namespace="cache"):
        self.lists[key] = self.lists.get(key, [])[start : stop + 1]
        return True

    def list_range(self, key, start, stop, namespace="cache"):
        return self.lists.get(key, [])[start : stop + 1]

    def list_length(self, key, namespace="cache"):
        return len(self.lists.get(key, []))

    # -- hashes --
    def hash_set(self, key, field, value, namespace="cache"):
        self.hashes.setdefault(key, {})[field] = value
        return True

    def hash_get_all(self, key, namespace="cache"):
        return dict(self.hashes.get(key, {}))

    def hash_multi_get(self, key, fields, namespace="cache"):
        h = self.hashes.get(key, {})
        return [h.get(f) for f in fields]

    def hash_length(self, key, namespace="cache"):
        return len(self.hashes.get(key, {}))

    # -- misc --
    def expire(self, key, ttl_hours, namespace="cache"):
        return True

    def delete_multi(self, keys, namespace="cache"):
        for k in keys:
            self.lists.pop(k, None)
            self.hashes.pop(k, None)
        return True

    def info(self):
        return {"fake": True}


@pytest.fixture
def mem():
    m = ShortTermMemory.__new__(ShortTermMemory)
    m._redis = FakeRedis()
    m.ttl_hours = 2
    m.max_messages = 100
    m.migration_threshold = 50
    m._user_id = None
    return m


def _seed(mem, n, user_id="u1"):
    for i in range(n):
        assert mem.add_interaction(
            user_query=f"q{i}", agent_response=f"r{i}", user_id=user_id
        ) is True


# -- Working memory -----------------------------------------------------------


def test_working_payload_empty_history(mem):
    payload = mem.build_working_payload("Ai là tác giả của nó?", user_id="u1")
    assert payload["turn_id"] is None
    assert payload["previous_user_query"] == ""
    assert payload["previous_system_response"] == ""
    assert payload["current_raw_query"] == "Ai là tác giả của nó?"


def test_working_payload_last_turn(mem):
    _seed(mem, 3, user_id="u1")
    payload = mem.build_working_payload("Ai là tác giả của nó?", user_id="u1")
    assert payload["previous_user_query"] == "q2"
    assert payload["previous_system_response"] == "r2"
    assert payload["current_raw_query"] == "Ai là tác giả của nó?"
    assert payload["turn_id"] is not None


def test_working_payload_per_user_isolation(mem):
    _seed(mem, 1, user_id="alice")
    payload = mem.build_working_payload("hello?", user_id="bob")
    assert payload["turn_id"] is None
    assert payload["previous_user_query"] == ""


def test_get_last_turn_none(mem):
    assert mem.get_last_turn(user_id="ghost") is None


# -- Sliding window -----------------------------------------------------------


def test_sliding_window_chronological_order(mem):
    _seed(mem, 7, user_id="u1")
    turns = mem.get_last_k_turns(k=5, user_id="u1")
    assert [t["user_query"] for t in turns] == ["q2", "q3", "q4", "q5", "q6"]


def test_sliding_window_default_size(mem):
    _seed(mem, 10, user_id="u1")
    turns = mem.get_last_k_turns(user_id="u1")
    assert len(turns) == DEFAULT_WINDOW_SIZE


def test_sliding_window_k_larger_than_history(mem):
    _seed(mem, 2, user_id="u1")
    turns = mem.get_last_k_turns(k=5, user_id="u1")
    assert [t["user_query"] for t in turns] == ["q0", "q1"]


def test_sliding_window_invalid_k(mem):
    _seed(mem, 2, user_id="u1")
    assert mem.get_last_k_turns(k=0, user_id="u1") == []
    assert mem.get_last_k_turns(k=-3, user_id="u1") == []


def test_sliding_window_per_user(mem):
    _seed(mem, 3, user_id="alice")
    _seed(mem, 1, user_id="bob")
    assert len(mem.get_last_k_turns(k=5, user_id="bob")) == 1
    assert len(mem.get_last_k_turns(k=5, user_id="alice")) == 3


# -- Summary state ------------------------------------------------------------


def test_summary_empty(mem):
    assert mem.get_summary(user_id="u1") == {"entities": [], "topics": [], "updated_at": None}


def test_summary_update_and_merge(mem):
    first = mem.update_summary(user_id="u1", entities=["HPG", "VCB"], topics=["steel"])
    assert first["entities"] == ["HPG", "VCB"]
    second = mem.update_summary(user_id="u1", entities=["VCB", "FPT"], topics=["bank"])
    # union, no duplicates, old items preserved
    assert second["entities"] == ["HPG", "VCB", "FPT"]
    assert second["topics"] == ["steel", "bank"]
    assert second["updated_at"] is not None
    assert mem.get_summary(user_id="u1") == second


def test_summary_per_user(mem):
    mem.update_summary(user_id="alice", entities=["HPG"])
    assert mem.get_summary(user_id="bob")["entities"] == []
