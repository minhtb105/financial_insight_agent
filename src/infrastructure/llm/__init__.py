__all__ = [
    "LLMProvider",
    "MultiQuery",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "LLMProvider": ".llm_provider",
        "MultiQuery": ".llm_provider",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
