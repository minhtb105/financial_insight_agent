"""
Structured logging implementation for the financial insight agent.

Provides JSON logging with correlation IDs, request tracing, and
production-ready log formatting.
"""

import json
import logging
import time
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
import os
import platform
from contextvars import ContextVar

# Context variables for request tracing
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)

logger = logging.getLogger(__name__)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def __init__(self, service_name: str = "financial_insight_agent"):
        super().__init__()
        self.service_name = service_name
        self.hostname = platform.node()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        session_id = session_id_var.get()

        # Base log structure
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "service": self.service_name,
            "hostname": self.hostname,
            "process_id": os.getpid(),
            "thread_id": threading.get_ident(),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context variables if available
        if request_id:
            log_data["request_id"] = request_id
        if user_id:
            log_data["user_id"] = user_id
        if session_id:
            log_data["session_id"] = session_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "getMessage",
                ]:
                    log_data[key] = value

        try:
            return json.dumps(log_data, ensure_ascii=False, default=str)
        except (TypeError, ValueError, RecursionError) as e:
            log_data["message"] = f"Log serialization failed: {e}"
            log_data["original_message"] = record.getMessage()
            return json.dumps(log_data, ensure_ascii=False, default=str)


class CorrelationFilter(logging.Filter):
    """Filter to add correlation IDs to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation IDs to log record."""
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.session_id = session_id_var.get()
        return True


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, operation_name: str, logger: logging.Logger):
        self.operation_name = operation_name
        self.logger = logger
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000  # Convert to milliseconds

        log_data = {
            "operation": self.operation_name,
            "duration_ms": round(duration, 2),
            "status": "completed" if exc_type is None else "failed",
        }

        if exc_type:
            log_data["error"] = str(exc_val)

        self.logger.info("Operation completed", extra=log_data)


class RequestLogger:
    """Logger wrapper with request context."""

    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)

    def set_request_context(
        self, request_id: str, user_id: str | None = None, session_id: str | None = None
    ):
        """Set request context for correlation."""
        request_id_var.set(request_id)
        if user_id:
            user_id_var.set(user_id)
        if session_id:
            session_id_var.set(session_id)

    def clear_request_context(self):
        """Clear request context."""
        request_id_var.set(None)
        user_id_var.set(None)
        session_id_var.set(None)

    def start_request(self, user_id: str | None = None, session_id: str | None = None) -> str:
        """Start a new request and return request ID."""
        request_id = str(uuid.uuid4())
        self.set_request_context(request_id, user_id, session_id)

        self.logger.info(
            "Request started",
            extra={"event": "request_started", "user_id": user_id, "session_id": session_id},
        )

        return request_id

    def end_request(self, status: str = "completed", error: str | None = None):
        """End current request."""
        self.logger.info(
            "Request ended", extra={"event": "request_ended", "status": status, "error": error}
        )
        self.clear_request_context()

    def info(self, message: str, *args, **kwargs):
        """Log info message with context."""
        if args:
            message = message % args
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log warning message with context."""
        if args:
            message = message % args
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log error message with context."""
        if args:
            message = message % args
        self.logger.error(message, extra=kwargs)

    def exception(self, message: str, *args, **kwargs):
        """Log exception message with traceback."""
        if args:
            message = message % args
        self.logger.exception(message, extra=kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Log debug message with context."""
        if args:
            message = message % args
        self.logger.debug(message, extra=kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log critical message with context."""
        if args:
            message = message % args
        self.logger.critical(message, extra=kwargs)

    def performance_timer(self, operation_name: str) -> PerformanceTimer:
        """Create performance timer for operation."""
        return PerformanceTimer(operation_name, self.logger)


def setup_logging(
    log_level: str = "INFO",
    log_file: str | None = None,
    service_name: str = "financial_insight_agent",
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """
    Setup structured logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        service_name: Name of the service
        enable_console: Enable console logging
        enable_file: Enable file logging
    """
    # Ensure log directory exists
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = JSONFormatter(service_name)

    # Create handlers
    handlers = []

    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(CorrelationFilter())
        handlers.append(console_handler)

    if enable_file and log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(CorrelationFilter())
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Only add handlers if root logger has none (avoid wiping pre-configured handlers)
    if not root_logger.handlers:
        for handler in handlers:
            root_logger.addHandler(handler)
    else:
        logger.debug("Root logger already has handlers — skipping setup")

    # Configure specific loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_file": log_file,
            "service_name": service_name,
            "handlers": len(handlers),
        },
    )


def get_logger(name: str) -> RequestLogger:
    """
    Get a logger instance with request context support.

    Args:
        name: Logger name

    Returns:
        RequestLogger instance
    """
    return RequestLogger(name)


