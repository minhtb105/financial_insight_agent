__version__ = "1.0.0"
__author__ = "Financial Insight Team"

__all__ = [
    "build_graph",
    "VNStockClient",
    "ConsoleApp",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "build_graph": "application.agents.agent",
        "VNStockClient": "infrastructure.api_clients.vn_stock_client",
        "ConsoleApp": "interfaces.cli.console",
    }
    if name in _LAZY:
        mod = importlib.import_module(f".{_LAZY[name]}", __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
