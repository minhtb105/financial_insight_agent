"""
Observability infrastructure for the financial insight agent.

Provides comprehensive logging, metrics collection, and alerting capabilities
for production-ready monitoring and debugging.
"""

from .logging.logger import setup_logging, get_logger
from .metrics.collector import MetricsCollector
from .alerting.manager import AlertManager

__all__ = [
    'setup_logging',
    'get_logger',
    'MetricsCollector',
    'AlertManager'
]