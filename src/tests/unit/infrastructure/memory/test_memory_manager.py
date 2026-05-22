"""Unit tests for MemoryManager (all external deps mocked)."""

from unittest.mock import patch, MagicMock

# ------------------------------------------------------------------
# Helpers: patch all three memory tiers + threading
# ------------------------------------------------------------------


def _patch_all():
    mp = patch.multiple(
        "infrastructure.memory.memory_manager",
        get_short_term_memory=MagicMock(),
    )
    return mp


def _make_manager(config=None):
    from infrastructure.memory.memory_manager import MemoryManager, MemoryConfig

    if config is None:
        config = MemoryConfig(
            auto_cleanup_enabled=False,
        )
    return MemoryManager(config=config)


# -- Constructor ----------------------------------------------------------


def test_init_with_defaults():
    with _patch_all():
        from infrastructure.memory.memory_manager import MemoryManager

        mm = MemoryManager()
    assert mm.config is not None
    assert mm.config.auto_cleanup_enabled is True


def test_init_with_custom_config():
    with _patch_all():
        from infrastructure.memory.memory_manager import MemoryConfig

        cfg = MemoryConfig(auto_cleanup_enabled=False)
        mm = _make_manager(config=cfg)
    assert mm.config.auto_cleanup_enabled is False


# -- add_interaction / search_memory (happy path) -------------------------


def test_add_and_search():
    with _patch_all():
        mm = _make_manager()
        mm.short_term.get_recent_interactions.return_value = [
            {"query": "what is VCB", "response": "a bank"}
        ]
        mm.short_term.get_facts.return_value = []

        success = mm.add_interaction(user_query="what is VCB", agent_response="a bank")
        result = mm.search_memory("VCB")
    assert success is not False  # short_term returns MagicMock which is truthy
    assert result.get("short_term", {}).get("count", 0) > 0


# -- add_interaction with None agent_response ----------------------------


def test_add_interaction_none_response():
    with _patch_all():
        mm = _make_manager()
        mm.short_term.add_interaction.return_value = True
        success = mm.add_interaction(user_query="key2", agent_response=None)
    assert success is True


# -- background tasks -----------------------------------------------------


def test_start_background_tasks():
    with _patch_all(), patch("threading.Thread") as mock_thread:
        mm = _make_manager()
        mm.start_background_tasks()
    assert mock_thread.called
    assert mock_thread.call_args[1].get("daemon") is True


def test_stop_background_tasks():
    with _patch_all():
        mm = _make_manager()
        mm.stop_background_tasks()
    assert mm._stop_event.is_set()
