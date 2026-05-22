"""Unit tests for CircuitBreaker."""

from infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitState


def test_initial_state_closed():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=10)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.total_failures == 0
    assert cb.total_successes == 0


def test_acquire_permit_when_closed():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=10)
    assert cb.acquire_permit() is True


def test_opens_after_threshold():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=10)
    cb.record_failure()
    cb.record_failure()
    assert cb.acquire_permit() is False


def test_single_failure_does_not_open():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=10)
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.acquire_permit() is True


def test_success_resets():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=10)
    cb.record_failure()
    cb.record_success()
    assert cb.acquire_permit() is True
    assert cb.failure_count == 0


def test_half_open_on_recovery():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0)
    cb.record_failure()
    assert cb.acquire_permit() is True


def test_half_open_allows_one_request():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0)
    cb.record_failure()
    assert cb.acquire_permit() is True
    assert cb.acquire_permit() is False


def test_half_open_success_closes():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0)
    cb.record_failure()
    cb.acquire_permit()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_half_open_failure_reopens():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.acquire_permit() is True
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_record_success_in_half_open_closes():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0)
    cb.record_failure()
    cb.acquire_permit()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_get_metrics():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=30)
    cb.record_success()
    cb.record_failure()
    metrics = cb.get_metrics()
    assert metrics["name"] == "test"
    assert metrics["state"] == "closed"
    assert metrics["total_successes"] == 1
    assert metrics["total_failures"] == 1
    assert metrics["failure_count"] == 1
    assert metrics["failure_threshold"] == 3
    assert metrics["recovery_timeout"] == 30
