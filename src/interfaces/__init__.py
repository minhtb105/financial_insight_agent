__all__ = [
    "ConsoleApp",
]


def __getattr__(name):
    import importlib

    if name == "ConsoleApp":
        mod = importlib.import_module(".cli.console", __package__)
        return getattr(mod, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
