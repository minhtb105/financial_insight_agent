import logging
import time
import threading
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LLMUnavailableError(Exception):
    def __init__(
        self,
        message: str = "No LLM providers available",
        provider_status: dict[str, str] | None = None,
    ):
        self.message = message
        self.provider_status = provider_status or {}
        super().__init__(self.message)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_requests: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        self._lock = threading.Lock()

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_last_changed_at = time.time()

    def is_open(self) -> bool:
        with self._lock:
            return self.state == CircuitState.OPEN

    def acquire_permit(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                if time.time() - self.state_last_changed_at >= self.recovery_timeout:
                    logger.info("Circuit %s transitioning OPEN -> HALF_OPEN", self.name)
                    self.state = CircuitState.HALF_OPEN
                    self.failure_count = 0
                    self.half_open_requests = 0
                    self.state_last_changed_at = time.time()
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                if time.time() - self.state_last_changed_at >= self.recovery_timeout and self.half_open_requests <= 0:
                    logger.info("Circuit %s HALF_OPEN probe timed out — back to OPEN", self.name)
                    self.state = CircuitState.OPEN
                    self.state_last_changed_at = time.time()
                    self.half_open_requests = 0
                    return False
                if self.half_open_requests < self.half_open_max_requests:
                    self.half_open_requests += 1
                    return True
                return False

            return False

    def record_success(self):
        with self._lock:
            self.total_successes += 1
            if self.state == CircuitState.CLOSED:
                return
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_requests -= 1
                if self.half_open_requests <= 0:
                    logger.info("Circuit %s recovered — HALF_OPEN -> CLOSED", self.name)
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.half_open_requests = 0
                    self.state_last_changed_at = time.time()
                else:
                    logger.info(
                        "Circuit %s HALF_OPEN probe succeeded (%d remaining)",
                        self.name,
                        self.half_open_requests,
                    )

    def record_failure(self):
        with self._lock:
            self.total_failures += 1
            self.last_failure_time = time.time()
            self.failure_count += 1

            if self.failure_count >= self.failure_threshold:
                if self.state != CircuitState.OPEN:
                    logger.warning(
                        "Circuit %s OPEN after %d consecutive failures",
                        self.name,
                        self.failure_count,
                    )
                self.state = CircuitState.OPEN
                self.state_last_changed_at = time.time()
            elif self.state == CircuitState.HALF_OPEN:
                logger.warning("Circuit %s HALF_OPEN probe failed — back to OPEN", self.name)
                self.state = CircuitState.OPEN
                self.state_last_changed_at = time.time()

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "total_failures": self.total_failures,
                "total_successes": self.total_successes,
                "last_failure_time": self.last_failure_time,
            }


def create_circuit_breaker(
    name: str,
    failure_threshold: int = 3,
    recovery_timeout: int = 60,
    half_open_max_requests: int = 1,
) -> CircuitBreaker:
    """Factory helper for consistent CircuitBreaker creation."""
    return CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_requests=half_open_max_requests,
    )
