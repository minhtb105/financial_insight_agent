__all__ = [
    "VNStockClient",
]


def __getattr__(name):
    import importlib

    if name == "VNStockClient":
        mod = importlib.import_module(".api_clients.vn_stock_client", __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
