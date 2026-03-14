"""
Alerting system for the financial insight agent.

Provides configurable alert rules, multiple notification channels,
and alert management capabilities.
"""

import time
import threading
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    FIRING = "firing"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Represents an alert."""
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    started_at: datetime
    ended_at: Optional[datetime] = None
    silenced: bool = False
    silenced_until: Optional[datetime] = None


@dataclass
class AlertRule:
    """Defines an alert rule."""
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[Dict[str, Any]], bool]
    labels: Dict[str, str]
    annotations: Dict[str, str]
    evaluate_interval_seconds: int = 60
    for_duration_seconds: int = 300  # 5 minutes
    enabled: bool = True


class NotificationChannel:
    """Base class for notification channels."""
    
    def __init__(self, name: str):
        self.name = name
    
    def send(self, alert: Alert) -> bool:
        """Send notification for alert."""
        raise NotImplementedError


class ConsoleNotificationChannel(NotificationChannel):
    """Console notification channel."""
    
    def send(self, alert: Alert) -> bool:
        """Send alert to console."""
        message = f"[{alert.severity.value.upper()}] {alert.name}: {alert.message}"
        if alert.labels:
            message += f" | Labels: {alert.labels}"
        if alert.annotations:
            message += f" | Annotations: {alert.annotations}"
        
        print(message)
        return True


class FileNotificationChannel(NotificationChannel):
    """File-based notification channel."""
    
    def __init__(self, name: str, file_path: str):
        super().__init__(name)
        self.file_path = file_path
    
    def send(self, alert: Alert) -> bool:
        """Send alert to file."""
        try:
            alert_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "alert_id": alert.id,
                "name": alert.name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "started_at": alert.started_at.isoformat(),
                "ended_at": alert.ended_at.isoformat() if alert.ended_at else None
            }
            
            with open(self.file_path, 'a') as f:
                f.write(json.dumps(alert_data, ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            logger.error(f"Failed to write alert to file {self.file_path}: {e}")
            return False


class AlertManager:
    """
    Alert manager that evaluates rules and sends notifications.
    """
    
    def __init__(self, metrics_collector=None):
        """
        Initialize alert manager.
        
        Args:
            metrics_collector: Metrics collector instance for rule evaluation
        """
        self.metrics_collector = metrics_collector
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_channels: List[NotificationChannel] = []
        self.silence_rules: Dict[str, datetime] = {}
        
        # Background evaluation thread
        self._evaluation_thread = None
        self._stop_event = threading.Event()
        
        # Default rules
        self._init_default_rules()
        
        logger.info("Initialized AlertManager")
    
    def _init_default_rules(self):
        """Initialize default alert rules."""
        default_rules = [
            AlertRule(
                name="HighErrorRate",
                description="High error rate detected",
                severity=AlertSeverity.ERROR,
                condition=self._check_error_rate,
                labels={"component": "api"},
                annotations={"runbook_url": "https://docs.example.com/runbooks/high-error-rate"},
                evaluate_interval_seconds=60,
                for_duration_seconds=300
            ),
            AlertRule(
                name="HighResponseTime",
                description="High response time detected",
                severity=AlertSeverity.WARNING,
                condition=self._check_response_time,
                labels={"component": "api"},
                annotations={"runbook_url": "https://docs.example.com/runbooks/high-response-time"},
                evaluate_interval_seconds=60,
                for_duration_seconds=300
            ),
            AlertRule(
                name="LowCacheHitRate",
                description="Cache hit rate is below threshold",
                severity=AlertSeverity.WARNING,
                condition=self._check_cache_hit_rate,
                labels={"component": "cache"},
                annotations={"runbook_url": "https://docs.example.com/runbooks/low-cache-hit-rate"},
                evaluate_interval_seconds=300,
                for_duration_seconds=600
            ),
            AlertRule(
                name="HighMemoryUsage",
                description="Memory usage is above threshold",
                severity=AlertSeverity.CRITICAL,
                condition=self._check_memory_usage,
                labels={"component": "system"},
                annotations={"runbook_url": "https://docs.example.com/runbooks/high-memory-usage"},
                evaluate_interval_seconds=300,
                for_duration_seconds=300
            ),
            AlertRule(
                name="SystemDown",
                description="System appears to be down",
                severity=AlertSeverity.CRITICAL,
                condition=self._check_system_health,
                labels={"component": "system"},
                annotations={"runbook_url": "https://docs.example.com/runbooks/system-down"},
                evaluate_interval_seconds=60,
                for_duration_seconds=120
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
    
    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel."""
        self.notification_channels.append(channel)
        logger.info(f"Added notification channel: {channel.name}")
    
    def remove_notification_channel(self, channel_name: str):
        """Remove a notification channel."""
        self.notification_channels = [c for c in self.notification_channels if c.name != channel_name]
        logger.info(f"Removed notification channel: {channel_name}")
    
    def silence_alert(self, alert_name: str, duration_minutes: int = 60):
        """Silence an alert for a specified duration."""
        silence_until = datetime.now() + timedelta(minutes=duration_minutes)
        self.silence_rules[alert_name] = silence_until
        logger.info(f"Silenced alert {alert_name} for {duration_minutes} minutes")
    
    def unsilence_alert(self, alert_name: str):
        """Remove silence for an alert."""
        if alert_name in self.silence_rules:
            del self.silence_rules[alert_name]
            logger.info(f"Unsilenced alert {alert_name}")
    
    def is_silenced(self, alert_name: str) -> bool:
        """Check if an alert is silenced."""
        if alert_name not in self.silence_rules:
            return False
        
        silenced_until = self.silence_rules[alert_name]
        if datetime.now() >= silenced_until:
            del self.silence_rules[alert_name]
            return False
        
        return True
    
    def start(self):
        """Start the alert manager."""
        if self._evaluation_thread is None:
            self._stop_event.clear()
            self._evaluation_thread = threading.Thread(target=self._evaluation_loop, daemon=True)
            self._evaluation_thread.start()
            logger.info("Started AlertManager")
    
    def stop(self):
        """Stop the alert manager."""
        if self._evaluation_thread is not None:
            self._stop_event.set()
            self._evaluation_thread.join(timeout=5)
            self._evaluation_thread = None
            logger.info("Stopped AlertManager")
    
    def _evaluation_loop(self):
        """Main evaluation loop."""
        while not self._stop_event.is_set():
            try:
                self._evaluate_rules()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                time.sleep(60)
    
    def _evaluate_rules(self):
        """Evaluate all alert rules."""
        current_time = datetime.now()
        
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            try:
                # Check if rule should be evaluated now
                last_eval_time = getattr(rule, '_last_eval_time', 0)
                if current_time.timestamp() - last_eval_time < rule.evaluate_interval_seconds:
                    continue
                
                rule._last_eval_time = current_time.timestamp()
                
                # Evaluate condition
                metrics_data = self._get_metrics_for_rule(rule)
                condition_result = rule.condition(metrics_data)
                
                # Handle alert state
                alert_key = f"{rule_name}"
                
                if condition_result:
                    # Condition is true, check if alert should be created
                    if alert_key not in self.active_alerts:
                        # Create new alert
                        alert = Alert(
                            id=f"{alert_key}_{int(time.time())}",
                            name=rule_name,
                            severity=rule.severity,
                            status=AlertStatus.FIRING,
                            message=rule.description,
                            labels=rule.labels,
                            annotations=rule.annotations,
                            started_at=current_time
                        )
                        self.active_alerts[alert_key] = alert
                        self._send_notifications(alert)
                        logger.warning(f"Alert fired: {rule_name}")
                    else:
                        # Update existing alert
                        alert = self.active_alerts[alert_key]
                        alert.status = AlertStatus.FIRING
                        alert.ended_at = None
                
                else:
                    # Condition is false, check if alert should be resolved
                    if alert_key in self.active_alerts:
                        alert = self.active_alerts[alert_key]
                        if alert.status == AlertStatus.FIRING:
                            alert.status = AlertStatus.RESOLVED
                            alert.ended_at = current_time
                            self._send_notifications(alert)
                            logger.info(f"Alert resolved: {rule_name}")
                            # Remove resolved alert after some time
                            if (current_time - alert.started_at).total_seconds() > 300:  # 5 minutes
                                del self.active_alerts[alert_key]
            
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_name}: {e}")
    
    def _get_metrics_for_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """Get relevant metrics for a rule."""
        if not self.metrics_collector:
            return {}
        
        # Get recent metrics (last 5 minutes)
        recent_metrics = self.metrics_collector.get_all_metrics()
        return recent_metrics
    
    def _send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        # Check if alert is silenced
        if self.is_silenced(alert.name):
            logger.debug(f"Alert {alert.name} is silenced, skipping notifications")
            return
        
        # Send to all notification channels
        for channel in self.notification_channels:
            try:
                success = channel.send(alert)
                if success:
                    logger.debug(f"Sent alert {alert.name} to {channel.name}")
                else:
                    logger.warning(f"Failed to send alert {alert.name} to {channel.name}")
            except Exception as e:
                logger.error(f"Error sending alert {alert.name} to {channel.name}: {e}")
    
    # Default rule conditions
    
    def _check_error_rate(self, metrics_data: Dict[str, Any]) -> bool:
        """Check if error rate is high."""
        try:
            # Get request error rate from metrics
            error_count = metrics_data.get("metrics", {}).get("request_errors", {}).get("values", {}).get("{}", 0)
            total_count = metrics_data.get("metrics", {}).get("request_count", {}).get("values", {}).get("{}", 0)
            
            if total_count > 0:
                error_rate = error_count / total_count
                return error_rate > 0.05  # 5% error rate threshold
            
            return False
        except Exception:
            return False
    
    def _check_response_time(self, metrics_data: Dict[str, Any]) -> bool:
        """Check if response time is high."""
        try:
            # Get 95th percentile response time
            stats = self.metrics_collector.get_histogram_stats("request_duration_seconds", time_window_minutes=5)
            p95 = stats.get("p95", 0)
            return p95 > 2.0  # 2 seconds threshold
        except Exception:
            return False
    
    def _check_cache_hit_rate(self, metrics_data: Dict[str, Any]) -> bool:
        """Check if cache hit rate is low."""
        try:
            hit_rate = metrics_data.get("metrics", {}).get("cache_hit_rate", {}).get("values", {}).get("{}", 0)
            return hit_rate < 0.8  # 80% threshold
        except Exception:
            return False
    
    def _check_memory_usage(self, metrics_data: Dict[str, Any]) -> bool:
        """Check if memory usage is high."""
        try:
            memory_usage = metrics_data.get("metrics", {}).get("memory_usage_percent", {}).get("values", {}).get("{}", 0)
            return memory_usage > 80  # 80% threshold
        except Exception:
            return False
    
    def _check_system_health(self, metrics_data: Dict[str, Any]) -> bool:
        """Check if system appears to be down."""
        try:
            # Check if we have recent metrics (system might be down if no recent data)
            last_metric_time = metrics_data.get("timestamp", 0)
            time_since_last_metric = time.time() - last_metric_time
            return time_since_last_metric > 300  # 5 minutes threshold
        except Exception:
            return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # This is a simplified implementation
        # In a real system, you'd want to store alert history persistently
        active_alerts = [a for a in self.active_alerts.values() if a.started_at >= cutoff_time]
        
        return active_alerts
    
    def get_rules_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all rules."""
        status = {}
        
        for rule_name, rule in self.rules.items():
            status[rule_name] = {
                "enabled": rule.enabled,
                "severity": rule.severity.value,
                "description": rule.description,
                "active": rule_name in self.active_alerts,
                "silenced": self.is_silenced(rule_name)
            }
        
        return status
    
    def clear_all_alerts(self):
        """Clear all active alerts."""
        self.active_alerts.clear()
        logger.info("Cleared all active alerts")


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(metrics_collector=None) -> Optional[AlertManager]:
    """Get global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        try:
            _alert_manager = AlertManager(metrics_collector)
            _alert_manager.add_notification_channel(ConsoleNotificationChannel("console"))
            _alert_manager.start()
        except Exception as e:
            logger.error(f"Failed to create alert manager: {e}")
            _alert_manager = None
    return _alert_manager


def set_alert_manager_instance(manager: AlertManager) -> None:
    """Set global alert manager instance (for testing)."""
    global _alert_manager
    _alert_manager = manager