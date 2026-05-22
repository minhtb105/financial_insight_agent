"""
Metrics collection system for the financial insight agent.

Provides Prometheus-compatible metrics for monitoring system performance,
cache efficiency, memory usage, and business metrics.
"""

import time
import logging
import threading
import statistics
from typing import Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Represents a single metric data point."""

    timestamp: float
    value: int | float
    labels: dict[str, str]


@dataclass
class MetricDefinition:
    """Defines a metric with its properties."""

    name: str
    description: str
    metric_type: str  # gauge, counter, histogram
    unit: str = ""
    labels: list[str] = None


class MetricsCollector:
    """
    Prometheus-compatible metrics collector with in-memory storage
    and export capabilities.
    """

    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics collector.

        Args:
            retention_hours: Hours to retain metric data
        """
        self.retention_hours = retention_hours
        self.retention_seconds = retention_hours * 3600

        # Metric storage
        self.metrics: dict[str, list[MetricPoint]] = {}
        self.metric_definitions: dict[str, MetricDefinition] = {}

        # Counters
        self.counters: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Gauges
        self.gauges: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Histograms
        self.histograms: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

        # Rate calculations
        self.rate_counters: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Lock for thread safety
        self._lock = threading.RLock()

        # Cleanup thread
        self._stop_event = threading.Event()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

        # Initialize default metrics
        self._init_default_metrics()

        logger.info(f"Initialized MetricsCollector with {retention_hours}h retention")

    def _init_default_metrics(self):
        """Initialize default system metrics."""
        default_metrics = [
            # System metrics
            MetricDefinition(
                "request_duration_seconds", "Request processing duration", "histogram", "seconds"
            ),
            MetricDefinition("request_count", "Total number of requests", "counter"),
            MetricDefinition("request_errors", "Number of failed requests", "counter"),
            MetricDefinition("cache_hit_rate", "Cache hit rate percentage", "gauge", "percent"),
            MetricDefinition("memory_usage_mb", "Memory usage in megabytes", "gauge", "MB"),
            MetricDefinition("cpu_usage_percent", "CPU usage percentage", "gauge", "percent"),
            # Cache metrics
            MetricDefinition("cache_operations_total", "Total cache operations", "counter"),
            MetricDefinition("cache_hits_total", "Total cache hits", "counter"),
            MetricDefinition("cache_misses_total", "Total cache misses", "counter"),
            MetricDefinition("cache_size", "Current cache size", "gauge"),
            # Memory metrics
            MetricDefinition("memory_operations_total", "Total memory operations", "counter"),
            MetricDefinition("memory_hits_total", "Total memory hits", "counter"),
            MetricDefinition("memory_misses_total", "Total memory misses", "counter"),
            MetricDefinition("episodes_count", "Number of episodes in episodic memory", "gauge"),
            MetricDefinition("company_profiles_count", "Number of company profiles", "gauge"),
            # Business metrics
            MetricDefinition("query_type_distribution", "Distribution of query types", "counter"),
            MetricDefinition("user_sessions_active", "Number of active user sessions", "gauge"),
            MetricDefinition(
                "agent_response_time_seconds", "Agent response time", "histogram", "seconds"
            ),
        ]

        for metric in default_metrics:
            self.register_metric(metric)

    def register_metric(self, definition: MetricDefinition):
        """Register a new metric definition."""
        with self._lock:
            self.metric_definitions[definition.name] = definition
            if definition.name not in self.metrics:
                self.metrics[definition.name] = []

    def increment_counter(self, name: str, value: int = 1, labels: dict[str, str] | None = None):
        """Increment a counter metric."""
        label_key = self._dict_to_key(labels or {})

        with self._lock:
            self.counters[name][label_key] += value

            # Also store as time series for historical data
            self._add_metric_point(name, self.counters[name][label_key], labels or {})

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None):
        """Set a gauge metric value."""
        label_key = self._dict_to_key(labels or {})

        with self._lock:
            self.gauges[name][label_key] = value
            self._add_metric_point(name, value, labels or {})

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None):
        """Record a histogram observation."""
        label_key = self._dict_to_key(labels or {})

        with self._lock:
            if name not in self.histograms:
                self.histograms[name] = defaultdict(list)

            self.histograms[name][label_key].append(value)
            self._add_metric_point(name, value, labels or {})

    def _add_metric_point(self, name: str, value: int | float, labels: dict[str, str]):
        metric_point = MetricPoint(timestamp=time.time(), value=value, labels=labels)

        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(metric_point)
        self._trim_metric_points(name)

    def _trim_metric_points(self, name: str, max_points: int = 10000):
        series = self.metrics.get(name, [])
        if len(series) > max_points:
            self.metrics[name] = series[-max_points:]

    def get_metric_value(
        self, name: str, labels: dict[str, str] | None = None
    ) -> int | float | None:
        """Get current value of a metric."""
        label_key = self._dict_to_key(labels or {})

        with self._lock:
            if name in self.counters and label_key in self.counters[name]:
                return self.counters[name][label_key]
            elif name in self.gauges and label_key in self.gauges[name]:
                return self.gauges[name][label_key]

            return None

    def get_histogram_stats(
        self, name: str, labels: dict[str, str] | None = None, time_window_minutes: int = 60
    ) -> dict[str, float]:
        """Get histogram statistics for a time window."""
        label_key = self._dict_to_key(labels or {})
        cutoff_time = time.time() - (time_window_minutes * 60)

        with self._lock:
            if name not in self.histograms or label_key not in self.histograms[name]:
                return {}

            # Get recent values
            recent_values = []
            if name in self.metrics:
                for point in self.metrics[name]:
                    if point.timestamp >= cutoff_time and point.labels == (labels or {}):
                        recent_values.append(point.value)

            if not recent_values:
                return {}

            return {
                "count": len(recent_values),
                "sum": sum(recent_values),
                "mean": statistics.mean(recent_values),
                "median": statistics.median(recent_values),
                "min": min(recent_values),
                "max": max(recent_values),
                "std_dev": statistics.stdev(recent_values) if len(recent_values) > 1 else 0.0,
                "p50": self._percentile(recent_values, 50),
                "p90": self._percentile(recent_values, 90),
                "p95": self._percentile(recent_values, 95),
                "p99": self._percentile(recent_values, 99),
            }

    def get_rate(
        self, name: str, labels: dict[str, str] | None = None, time_window_minutes: int = 5
    ) -> float:
        """Calculate rate of change for a counter."""
        with self._lock:
            cutoff_time = time.time() - (time_window_minutes * 60)

            if name not in self.metrics:
                return 0.0

            # Get recent values
            recent_points = []
            for point in self.metrics[name]:
                if point.timestamp >= cutoff_time and point.labels == (labels or {}):
                    recent_points.append(point)

            if len(recent_points) < 2:
                return 0.0

            # Sort by timestamp
            recent_points.sort(key=lambda x: x.timestamp)

            # Calculate rate
            time_diff = recent_points[-1].timestamp - recent_points[0].timestamp
            if time_diff <= 0:
                return 0.0

            value_diff = recent_points[-1].value - recent_points[0].value
            rate = value_diff / time_diff

            return rate

    def get_time_series(
        self, name: str, labels: dict[str, str] | None = None, time_window_hours: int = 1
    ) -> list[MetricPoint]:
        """Get time series data for a metric."""
        cutoff_time = time.time() - (time_window_hours * 3600)

        with self._lock:
            if name not in self.metrics:
                return []

            result = []
            target_labels = labels or {}

            for point in self.metrics[name]:
                if point.timestamp >= cutoff_time and point.labels == target_labels:
                    result.append(point)

            return sorted(result, key=lambda x: x.timestamp)

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics with their current values and metadata."""
        with self._lock:
            result = {
                "timestamp": time.time(),
                "retention_hours": self.retention_hours,
                "metrics": {},
                "definitions": {},
            }

            # Add metric definitions
            for name, definition in self.metric_definitions.items():
                result["definitions"][name] = asdict(definition)

            # Add current values
            for name in self.metrics:
                if name in self.counters:
                    result["metrics"][name] = {
                        "type": "counter",
                        "values": dict(self.counters[name]),
                    }
                elif name in self.gauges:
                    result["metrics"][name] = {"type": "gauge", "values": dict(self.gauges[name])}
                elif name in self.histograms:
                    result["metrics"][name] = {
                        "type": "histogram",
                        "values": {k: len(v) for k, v in self.histograms[name].items()},
                    }

            return result

    def _dict_to_key(self, d: dict[str, str]) -> str:
        """Convert dictionary to string key for internal storage."""
        if not d:
            return ""
        return json.dumps(d, sort_keys=True)

    def _key_to_dict(self, key: str) -> dict[str, str]:
        """Convert string key back to dictionary."""
        if not key:
            return {}
        return json.loads(key)

    def _format_labels(self, labels: dict[str, str]) -> str:
        """Format labels for Prometheus output."""
        if not labels:
            return ""

        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"

    def _percentile(self, data: list[float], p: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((p / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def stop(self):
        """Stop the metrics collector."""
        self._stop_event.set()
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Stopped MetricsCollector")

    def _cleanup_loop(self):
        """Background cleanup of old metric data."""
        while not self._stop_event.is_set():
            try:
                self._cleanup_old_data()
                self._stop_event.wait(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
                if self._stop_event.wait(60):  # Wait 1 minute before retrying
                    break

    def _cleanup_old_data(self):
        """Remove old metric data beyond retention period."""
        cutoff_time = time.time() - self.retention_seconds

        with self._lock:
            cleaned_count = 0

            for metric_name in list(self.metrics.keys()):
                old_points = [p for p in self.metrics[metric_name] if p.timestamp < cutoff_time]
                if old_points:
                    self.metrics[metric_name] = [
                        p for p in self.metrics[metric_name] if p.timestamp >= cutoff_time
                    ]
                    cleaned_count += len(old_points)

            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} old metric points")

    def record_request_metrics(
        self,
        request_type: str,
        duration: float,
        success: bool = True,
        error_type: str | None = None,
    ):
        """Record request-level metrics."""
        labels = {"request_type": request_type}

        # Record duration histogram
        self.observe_histogram("request_duration_seconds", duration, labels)

        # Record success/failure counts
        if success:
            self.increment_counter("request_count", 1, labels)
        else:
            self.increment_counter("request_errors", 1, labels)
            if error_type:
                error_labels = {**labels, "error_type": error_type}
                self.increment_counter("request_errors", 1, error_labels)


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector | None:
    """Get metrics collector instance — prefer Dependencies container, fallback to global singleton."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    if deps is not None and deps.metrics_collector is not None:
        return deps.metrics_collector

    global _metrics_collector
    if _metrics_collector is None:
        try:
            _metrics_collector = MetricsCollector()
        except Exception as e:
            logger.error(f"Failed to create metrics collector: {e}")
    return _metrics_collector


def set_metrics_collector_instance(collector: MetricsCollector) -> None:
    """Set global metrics collector instance (for testing / DI seeding)."""
    global _metrics_collector
    _metrics_collector = collector
