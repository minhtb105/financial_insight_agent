"""Unit tests for MemoryManager tiers (working/sliding/episodic)."""

from unittest.mock import MagicMock, patch

from infrastructure.memory.memory_manager import MemoryConfig, MemoryManager


def _make_manager(episodic=None):
    with patch(
        "infrastructure.memory.memory_manager.get_short_term_memory",
        return_value=MagicMock(),
    ):
        mm = MemoryManager(
            config=MemoryConfig(auto_cleanup_enabled=False, episodic_enabled=False)
        )
    mm.episodic = episodic
    return mm


def test_search_working_tier():
    mm = _make_manager()
    mm.short_term.build_working_payload.return_value = {
        "turn_id": "1",
        "previous_user_query": "q",
        "previous_system_response": "r",
        "current_raw_query": "q2?",
    }
    result = mm.search_memory("q2?", memory_tiers=["working"], user_id="u1")
    assert result["working"]["previous_user_query"] == "q"
    mm.short_term.build_working_payload.assert_called_once_with(
        current_raw_query="q2?", user_id="u1"
    )


def test_search_sliding_tier():
    mm = _make_manager()
    mm.short_term.get_last_k_turns.return_value = [{"user_query": "q0"}]
    mm.short_term.get_summary.return_value = {"entities": ["HPG"], "topics": [], "updated_at": None}
    result = mm.search_memory("q?", memory_tiers=["sliding"], user_id="u1")
    assert result["sliding"]["count"] == 1
    assert result["sliding"]["summary"]["entities"] == ["HPG"]
    mm.short_term.get_last_k_turns.assert_called_once_with(k=5, user_id="u1")


def test_search_episodic_unavailable():
    mm = _make_manager(episodic=None)
    result = mm.search_memory("HPG?", memory_tiers=["episodic"], user_id="u1")
    assert result["episodic"]["count"] == 0
    assert result["episodic"]["error"] == "unavailable"


def test_search_episodic_tier():
    fake = MagicMock()
    fake.search_episodes.return_value = {"hits": [{"id": "1"}], "context": "ctx", "count": 1}
    mm = _make_manager(episodic=fake)
    result = mm.search_memory("HPG?", memory_tiers=["episodic"], user_id="u1")
    assert result["episodic"]["count"] == 1
    fake.search_episodes.assert_called_once_with(query="HPG?", user_id="u1", top_k=5)


def test_search_short_term_backward_compat():
    mm = _make_manager()
    mm.short_term.get_recent_interactions.return_value = [{"user_query": "q"}]
    mm.short_term.get_facts.return_value = {"f": 1}
    result = mm.search_memory("q", user_id="u1")
    assert "short_term" in result
    assert result["short_term"]["count"] == 2


def test_build_reformulation_inputs_shape():
    fake = MagicMock()
    fake.search_episodes.return_value = {"hits": [], "context": "", "count": 0}
    mm = _make_manager(episodic=fake)
    mm.short_term.build_working_payload.return_value = {
        "turn_id": None,
        "previous_user_query": "",
        "previous_system_response": "",
        "current_raw_query": "Ai là tác giả?",
    }
    mm.short_term.get_last_k_turns.return_value = []
    mm.short_term.get_summary.return_value = {"entities": [], "topics": [], "updated_at": None}
    out = mm.build_reformulation_inputs("Ai là tác giả?", user_id="u1")
    assert set(out) == {"working", "sliding", "episodic"}
    assert out["working"]["current_raw_query"] == "Ai là tác giả?"
    assert out["sliding"]["count"] == 0


def test_clear_all_covers_episodic():
    fake = MagicMock()
    mm = _make_manager(episodic=fake)
    assert mm.clear_all(user_id="u1") is True
    mm.short_term.clear.assert_called_once_with(user_id="u1")
    fake.clear_user_episodes.assert_called_once_with("u1")


def test_get_stats_includes_episodic():
    fake = MagicMock()
    fake.count.return_value = 7
    mm = _make_manager(episodic=fake)
    mm.short_term.get_stats.return_value = {"message_count": 2}
    stats = mm.get_stats(user_id="u1")
    assert stats["tiers"]["episodic"] == {"count": 7}
    assert stats["config"]["window_size"] == 5
