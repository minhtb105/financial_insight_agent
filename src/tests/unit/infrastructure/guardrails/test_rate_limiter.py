"""Unit tests for RateLimiter."""

from infrastructure.guardrails.rate_limiter import RateLimiter
from infrastructure.guardrails.config import GuardrailConfig


def test_initial_state_passes():
    limiter = RateLimiter(GuardrailConfig())
    result = limiter.validate("test query", "127.0.0.1")
    assert result.passed is True


def test_hourly_limit():
    cfg = GuardrailConfig()
    cfg.rate_limit_hourly_per_ip = 2
    limiter = RateLimiter(cfg)
    limiter.validate("q1", "127.0.0.1")
    limiter.validate("q2", "127.0.0.1")
    result = limiter.validate("q3", "127.0.0.1")
    assert result.passed is False
