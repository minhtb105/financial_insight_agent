__all__ = [
    "build_graph",
]


def __getattr__(name):
    import importlib

    if name == "build_graph":
        mod = importlib.import_module(".agent", __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
