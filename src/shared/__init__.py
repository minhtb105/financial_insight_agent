__all__ = [
    "TimeProcessor",
    "calculate_std_dev",
    "calculate_volatility",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "TimeProcessor": ".utils.time_processor",
        "calculate_volatility": ".utils.calculations",
        "calculate_std_dev": ".utils.calculations",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
