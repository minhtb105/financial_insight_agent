__all__ = [
    "AlertManager",
    "MetricsCollector",
    "get_alert_manager",
    "get_logger",
    "get_metrics_collector",
    "init_observability",
    "setup_logging",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "setup_logging": ".logging.logger",
        "get_logger": ".logging.logger",
        "MetricsCollector": ".metrics.collector",
        "get_metrics_collector": ".metrics.collector",
        "AlertManager": ".alerting.manager",
        "get_alert_manager": ".alerting.manager",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def init_observability():
    from .logging.logger import get_logger, setup_logging
    from .metrics.collector import get_metrics_collector
    from .alerting.manager import get_alert_manager

    setup_logging()
    metrics_collector = get_metrics_collector()
    alert_manager = get_alert_manager(metrics_collector)
    logger = get_logger("observability")
    logger.info(
        "Observability initialized",
        extra={
            "metrics_collector": metrics_collector is not None,
            "alert_manager": alert_manager is not None,
        },
    )
    return alert_manager
