"""
Memory architecture for the financial insight agent.

Simplified to short-term Redis-backed memory only.
"""

__all__ = ["MemoryManager", "ShortTermMemory"]


def __getattr__(name):
    import importlib

    _LAZY = {
        "ShortTermMemory": ".short_term.memory",
        "MemoryManager": ".memory_manager",
        "memory_manager": ".memory_manager",
        "short_term": ".short_term.memory",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        if hasattr(mod, name):
            return getattr(mod, name)
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
