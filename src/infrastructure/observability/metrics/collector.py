"""
Metrics collection system for the financial insight agent.

Provides Prometheus-compatible metrics for monitoring system performance,
cache efficiency, memory usage, and business metrics.
"""

import time
import logging
import threading
import statistics
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Represents a single metric data point."""
    timestamp: float
    value: Union[int, float]
    labels: Dict[str, str]


@dataclass
class MetricDefinition:
    """Defines a metric with its properties."""
    name: str
    description: str
    metric_type: str  # gauge, counter, histogram
    unit: str = ""
    labels: List[str] = None


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
        self.metrics: Dict[str, List[MetricPoint]] = {}
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        
        # Counters
        self.counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Gauges
        self.gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Histograms
        self.histograms: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        # Rate calculations
        self.rate_counters: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # Initialize default metrics
        self._init_default_metrics()
        
        logger.info(f"Initialized MetricsCollector with {retention_hours}h retention")
    
    def _init_default_metrics(self):
        """Initialize default system metrics."""
        default_metrics = [
            # System metrics
            MetricDefinition("request_duration_seconds", "Request processing duration", "histogram", "seconds"),
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
            MetricDefinition("agent_response_time_seconds", "Agent response time", "histogram", "seconds"),
        ]
        
        for metric in default_metrics:
            self.register_metric(metric)
    
    def register_metric(self, definition: MetricDefinition):
        """Register a new metric definition."""
        with self._lock:
            self.metric_definitions[definition.name] = definition
            if definition.name not in self.metrics:
                self.metrics[definition.name] = []
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        label_key = self._dict_to_key(labels or {})
        
        with self._lock:
            self.counters[name][label_key] += value
            
            # Also store as time series for historical data
            self._add_metric_point(name, self.counters[name][label_key], labels or {})
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        label_key = self._dict_to_key(labels or {})
        
        with self._lock:
            self.gauges[name][label_key] = value
            self._add_metric_point(name, value, labels or {})
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram observation."""
        label_key = self._dict_to_key(labels or {})
        
        with self._lock:
            if name not in self.histograms:
                self.histograms[name] = defaultdict(list)
            
            self.histograms[name][label_key].append(value)
            self._add_metric_point(name, value, labels or {})
    
    def _add_metric_point(self, name: str, value: Union[int, float], labels: Dict[str, str]):
        """Add a metric point to the time series."""
        metric_point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels
        )
        
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(metric_point)
    
    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[Union[int, float]]:
        """Get current value of a metric."""
        label_key = self._dict_to_key(labels or {})
        
        with self._lock:
            if name in self.counters and label_key in self.counters[name]:
                return self.counters[name][label_key]
            elif name in self.gauges and label_key in self.gauges[name]:
                return self.gauges[name][label_key]
            
            return None
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None, 
                          time_window_minutes: int = 60) -> Dict[str, float]:
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
    
    def get_rate(self, name: str, labels: Optional[Dict[str, str]] = None, 
                time_window_minutes: int = 5) -> float:
        """Calculate rate of change for a counter."""
        label_key = self._dict_to_key(labels or {})
        cutoff_time = time.time() - (time_window_minutes * 60)
        
        with self._lock:
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
    
    def get_time_series(self, name: str, labels: Optional[Dict[str, str]] = None, 
                       time_window_hours: int = 1) -> List[MetricPoint]:
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
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics with their current values and metadata."""
        with self._lock:
            result = {
                "timestamp": time.time(),
                "retention_hours": self.retention_hours,
                "metrics": {},
                "definitions": {}
            }
            
            # Add metric definitions
            for name, definition in self.metric_definitions.items():
                result["definitions"][name] = asdict(definition)
            
            # Add current values
            for name in self.metrics.keys():
                if name in self.counters:
                    result["metrics"][name] = {
                        "type": "counter",
                        "values": dict(self.counters[name])
                    }
                elif name in self.gauges:
                    result["metrics"][name] = {
                        "type": "gauge", 
                        "values": dict(self.gauges[name])
                    }
                elif name in self.histograms:
                    result["metrics"][name] = {
                        "type": "histogram",
                        "values": {k: len(v) for k, v in self.histograms[name].items()}
                    }
            
            return result
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        with self._lock:
            lines = []
            
            # Add metric definitions as comments
            for name, definition in self.metric_definitions.items():
                lines.append(f"# HELP {name} {definition.description}")
                lines.append(f"# TYPE {name} {definition.metric_type}")
            
            # Add counter values
            for name, counter_dict in self.counters.items():
                for label_key, value in counter_dict.items():
                    labels = self._key_to_dict(label_key)
                    label_str = self._format_labels(labels)
                    lines.append(f"{name}{label_str} {value}")
            
            # Add gauge values
            for name, gauge_dict in self.gauges.items():
                for label_key, value in gauge_dict.items():
                    labels = self._key_to_dict(label_key)
                    label_str = self._format_labels(labels)
                    lines.append(f"{name}{label_str} {value}")
            
            return "\n".join(lines)
    
    def export_json(self) -> str:
        """Export metrics in JSON format."""
        return json.dumps(self.get_all_metrics(), indent=2, ensure_ascii=False)
    
    def _dict_to_key(self, d: Dict[str, str]) -> str:
        """Convert dictionary to string key for internal storage."""
        if not d:
            return ""
        return json.dumps(d, sort_keys=True)
    
    def _key_to_dict(self, key: str) -> Dict[str, str]:
        """Convert string key back to dictionary."""
        if not key:
            return {}
        return json.loads(key)
    
    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus output."""
        if not labels:
            return ""
        
        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"
    
    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((p / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _cleanup_loop(self):
        """Background cleanup of old metric data."""
        while True:
            try:
                self._cleanup_old_data()
                time.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _cleanup_old_data(self):
        """Remove old metric data beyond retention period."""
        cutoff_time = time.time() - self.retention_seconds
        
        with self._lock:
            cleaned_count = 0
            
            for metric_name in list(self.metrics.keys()):
                old_points = [p for p in self.metrics[metric_name] if p.timestamp < cutoff_time]
                if old_points:
                    self.metrics[metric_name] = [p for p in self.metrics[metric_name] if p.timestamp >= cutoff_time]
                    cleaned_count += len(old_points)
            
            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} old metric points")
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get system-level metrics (CPU, memory, etc.)."""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            
            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_mb": memory_mb,
                "memory_usage_percent": memory.percent,
                "disk_usage_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
            }
            
        except ImportError:
            logger.warning("psutil not available, returning mock system metrics")
            return {
                "cpu_usage_percent": 0.0,
                "memory_usage_mb": 0.0,
                "memory_usage_percent": 0.0,
                "disk_usage_percent": 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def record_business_metric(self, metric_name: str, value: Union[int, float], 
                             labels: Optional[Dict[str, str]] = None):
        """Record a business metric."""
        metric_def = MetricDefinition(
            name=metric_name,
            description=f"Business metric: {metric_name}",
            metric_type="gauge"
        )
        self.register_metric(metric_def)
        self.set_gauge(metric_name, value, labels)
    
    def record_cache_metrics(self, cache_stats: Dict[str, Any]):
        """Record cache performance metrics."""
        labels = {"cache_type": cache_stats.get("cache_type", "unknown")}
        
        # Record hit rate
        hit_rate = cache_stats.get("hit_rate", 0)
        self.set_gauge("cache_hit_rate", hit_rate, labels)
        
        # Record operations
        total_ops = cache_stats.get("total_requests", 0)
        hits = cache_stats.get("hits", 0)
        misses = cache_stats.get("misses", 0)
        
        self.increment_counter("cache_operations_total", total_ops, labels)
        self.increment_counter("cache_hits_total", hits, labels)
        self.increment_counter("cache_misses_total", misses, labels)
        
        # Record cache size
        cache_size = cache_stats.get("current_size", 0)
        self.set_gauge("cache_size", cache_size, labels)
    
    def record_memory_metrics(self, memory_stats: Dict[str, Any]):
        """Record memory system metrics."""
        # Record episode count
        episode_count = memory_stats.get("episodes", {}).get("total_episodes", 0)
        self.set_gauge("episodes_count", episode_count)
        
        # Record company profiles count
        company_count = memory_stats.get("company_profiles", {}).get("total_profiles", 0)
        self.set_gauge("company_profiles_count", company_count)
        
        # Record memory operations
        total_ops = memory_stats.get("total_operations", 0)
        self.increment_counter("memory_operations_total", total_ops)
    
    def record_request_metrics(self, request_type: str, duration: float, 
                             success: bool = True, error_type: Optional[str] = None):
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
    
    def record_query_metrics(self, query_type: str, response_time: float, 
                           success: bool = True):
        """Record query-specific metrics."""
        labels = {"query_type": query_type}
        
        # Record response time
        self.observe_histogram("agent_response_time_seconds", response_time, labels)
        
        # Record query type distribution
        if success:
            self.increment_counter("query_type_distribution", 1, labels)
    
    def clear(self):
        """Clear all metrics data."""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            logger.info("Cleared all metrics data")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        try:
            _metrics_collector = MetricsCollector()
        except Exception as e:
            logger.error(f"Failed to create metrics collector: {e}")
            _metrics_collector = None
    return _metrics_collector


def set_metrics_collector_instance(collector: MetricsCollector) -> None:
    """Set global metrics collector instance (for testing)."""
    global _metrics_collector
    _metrics_collector = collector