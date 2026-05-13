from .logging.logger import setup_logging, get_logger
from .metrics.collector import MetricsCollector, get_metrics_collector
from .alerting.manager import AlertManager, get_alert_manager

__all__ = [
    'setup_logging',
    'get_logger',
    'MetricsCollector',
    'AlertManager',
    'get_metrics_collector',
    'get_alert_manager',
    'init_observability',
]


def init_observability():
    setup_logging()
    metrics_collector = get_metrics_collector()
    alert_manager = get_alert_manager(metrics_collector)
    logger = get_logger("observability")
    logger.info("Observability initialized", extra={
        "metrics_collector": metrics_collector is not None,
        "alert_manager": alert_manager is not None,
    })
    return alert_manager