__all__ = [
    "TimeRange",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "TimeRange": ".entities.time_range",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
