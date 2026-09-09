"""Integration: memory inputs for Reformulation against real Redis + Qdrant.

Skips cleanly when infra is unavailable. Redis uses db=15; Qdrant uses an
isolated embedded dir under tmp_path (no docker needed).
"""

import time
import uuid

import pytest

pytestmark = pytest.mark.integration


def _redis_available():
    try:
        import redis

        redis.Redis(host="localhost", port=6379, db=15, socket_timeout=2).ping()
        return True
    except Exception:
        return False


@pytest.fixture
def user_id():
    return f"itest-{uuid.uuid4().hex[:8]}"


def test_working_and_sliding_against_redis(user_id):
    if not _redis_available():
        pytest.skip("Redis localhost:6379 unavailable")
    from infrastructure.memory.short_term.memory import ShortTermMemory

    mem = ShortTermMemory(host="localhost", port=6379, db=15)
    try:
        for i in range(5):
            assert mem.add_interaction(
                user_query=f"itest q{i}", agent_response=f"itest r{i}", user_id=user_id
            )

        payload = mem.build_working_payload("Ai là tác giả của nó?", user_id=user_id)
        assert payload["previous_user_query"] == "itest q4"
        assert payload["previous_system_response"] == "itest r4"
        assert payload["current_raw_query"] == "Ai là tác giả của nó?"
        assert payload["turn_id"] is not None

        turns = mem.get_last_k_turns(k=5, user_id=user_id)
        assert [t["user_query"] for t in turns] == [f"itest q{i}" for i in range(5)]

        summary = mem.update_summary(user_id=user_id, entities=["HPG"], topics=["steel"])
        assert summary["entities"] == ["HPG"]
        assert mem.get_summary(user_id=user_id)["topics"] == ["steel"]
    finally:
        mem.clear(user_id=user_id)
        mem.close()


def test_episodic_against_embedded_qdrant(user_id, tmp_path, monkeypatch):
    from infrastructure.memory.episodic.store import EpisodicStore
    from infrastructure.rag.embedder import Embedder

    try:
        embedder = Embedder()
    except Exception as e:
        pytest.skip(f"no embedding provider: {e}")
    if embedder.provider == "none":
        pytest.skip("no embedding provider available")

    monkeypatch.setenv("QDRANT_PATH", str(tmp_path / "qdrant"))
    monkeypatch.setenv("QDRANT_FORCE_LOCAL", "true")
    store = EpisodicStore(
        collection=f"itest_episodic_{uuid.uuid4().hex[:8]}",
        embedder=embedder,
        min_score=0.0,
    )
    texts = [
        "HPG là cổ phiếu ngành thép trên HOSE",
        "VCB là ngân hàng Vietcombank",
        "FPT là tập đoàn công nghệ thông tin",
    ]
    for t in texts:
        assert store.add_episode(user_id=user_id, text=t) is not None

    # wait briefly for embedded index visibility (usually immediate)
    deadline = time.time() + 10
    result = {"count": 0}
    while time.time() < deadline:
        result = store.search_episodes("cổ phiếu thép HPG", user_id=user_id, top_k=3)
        if result["count"] >= 1:
            break
        time.sleep(0.5)
    assert result["count"] >= 1
    assert all(h["payload"]["user_id"] == user_id for h in result["hits"])
    assert "thép" in result["context"] or "HPG" in result["context"]

    other = store.search_episodes("cổ phiếu thép HPG", user_id="ghost-user", top_k=3)
    assert other["count"] == 0

    assert store.count(user_id) == 3
    assert store.clear_user_episodes(user_id) == 3
    assert store.count(user_id) == 0


def test_manager_reformulation_inputs_end_to_end(user_id):
    if not _redis_available():
        pytest.skip("Redis localhost:6379 unavailable")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("QDRANT_FORCE_LOCAL", "true")
        from infrastructure.memory.memory_manager import MemoryConfig, MemoryManager
        from infrastructure.memory.short_term.memory import ShortTermMemory
        from unittest.mock import patch

        mem = ShortTermMemory(host="localhost", port=6379, db=15)
        try:
            mem.add_interaction(user_query="Khái niệm Transformer là gì?",
                                agent_response="Transformer là kiến trúc Attention...",
                                user_id=user_id)
            with patch(
                "infrastructure.memory.memory_manager.get_short_term_memory",
                return_value=mem,
            ):
                mgr = MemoryManager(
                    config=MemoryConfig(auto_cleanup_enabled=False, episodic_enabled=False)
                )
                out = mgr.build_reformulation_inputs("Ai là tác giả của nó?", user_id=user_id)
            assert out["working"]["previous_user_query"] == "Khái niệm Transformer là gì?"
            assert out["working"]["current_raw_query"] == "Ai là tác giả của nó?"
            assert out["sliding"]["count"] == 1
            assert out["episodic"]["error"] == "unavailable"
        finally:
            mem.clear(user_id=user_id)
            mem.close()
