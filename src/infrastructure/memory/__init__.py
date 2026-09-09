"""
Memory architecture for the financial insight agent.

Tiers:
- working / sliding: Redis-backed short-term turns (last-turn payload + window).
- episodic: Qdrant-backed semantic retrieval over past turns.
"""

__all__ = ["Episode", "EpisodicStore", "MemoryManager", "ShortTermMemory"]


def __getattr__(name):
    import importlib

    _LAZY = {
        "ShortTermMemory": ".short_term.memory",
        "MemoryManager": ".memory_manager",
        "memory_manager": ".memory_manager",
        "short_term": ".short_term.memory",
        "EpisodicStore": ".episodic.store",
        "Episode": ".episodic.schemas",
        "episodic": ".episodic.store",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        if hasattr(mod, name):
            return getattr(mod, name)
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
