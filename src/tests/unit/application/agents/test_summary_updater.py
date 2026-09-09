"""Unit tests for SummaryUpdater (memory manager mocked, never calls LLM)."""

from unittest.mock import MagicMock, patch

from application.agents.summary_updater import SummaryUpdater


def _manager_with_short_term():
    mgr = MagicMock()
    mgr._validated_user_id.side_effect = lambda uid: uid or "anonymous"
    mgr.short_term.update_summary.side_effect = lambda user_id, entities, topics: {
        "entities": entities,
        "topics": topics,
        "updated_at": "now",
    }
    return mgr


def test_update_passes_llm_entities():
    updater = SummaryUpdater()
    # SummaryUpdater imports get_memory_manager lazily from
    # infrastructure.memory.memory_manager, so patch that target.
    with patch(
        "infrastructure.memory.memory_manager.get_memory_manager",
        return_value=_manager_with_short_term(),
    ):
        out = updater.update(
            user_id="u1", entities=["HPG"], topics=["steel"],
            raw_query="Giá của nó?", rewritten_query="Giá HPG?",
        )
    assert out["entities"] == ["HPG"]
    assert out["topics"] == ["steel"]


def test_fallback_extracts_known_tickers():
    updater = SummaryUpdater()
    mgr = _manager_with_short_term()
    with patch(
        "infrastructure.memory.memory_manager.get_memory_manager", return_value=mgr
    ):
        out = updater.update(
            user_id="u1", entities=[], topics=[],
            raw_query="còn VIC thì sao?", rewritten_query="Giá VIC bao nhiêu?",
        )
    assert "VIC" in out["entities"]
    mgr.short_term.update_summary.assert_called_once()


def test_fallback_ignores_unknown_tokens():
    updater = SummaryUpdater()
    mgr = _manager_with_short_term()
    with patch(
        "infrastructure.memory.memory_manager.get_memory_manager", return_value=mgr
    ):
        out = updater.update(
            user_id="u1", entities=[], topics=[],
            raw_query="Ai là tác giả của nó?", rewritten_query="Ai là tác giả?",
        )
    assert out["entities"] == []


def test_no_manager_never_raises():
    updater = SummaryUpdater()
    with patch(
        "infrastructure.memory.memory_manager.get_memory_manager", return_value=None
    ):
        out = updater.update(user_id="u1", entities=["HPG"], topics=[], raw_query="q")
    assert out["entities"] == ["HPG"]


def test_extract_tickers_prefers_rewritten():
    from infrastructure.guardrails.tickers import VIETNAMESE_TICKERS

    found = SummaryUpdater._extract_tickers("còn nó thì sao?", "Giá HPG và VCB?", VIETNAMESE_TICKERS)
    assert found == ["HPG", "VCB"]
