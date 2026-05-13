import asyncio
import time
from collections import defaultdict

from .base import Guardrail, GuardrailResult
from .config import GuardrailConfig


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float, refill_period: float = 1.0):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.refill_period = refill_period
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * (self.refill_rate / self.refill_period),
            )
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimiter(Guardrail):
    def __init__(self, config: GuardrailConfig | None = None):
        cfg = config or GuardrailConfig()
        self.buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=cfg.rate_limit_burst,
                refill_rate=cfg.rate_limit_requests / cfg.rate_limit_window_seconds,
            )
        )
        self.hourly_counts: dict[str, tuple[int, float]] = {}
        self.hourly_limit = cfg.rate_limit_hourly_per_ip
        self.hourly_lock = asyncio.Lock()
        self.cleanup_lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return "rate_limiter"

    async def validate(self, query: str, client_ip: str) -> GuardrailResult:
        bucket = self.buckets[client_ip]
        if not await bucket.consume():
            return GuardrailResult(
                passed=False,
                reason="Too many requests. Please slow down.",
                status_code=429,
                metadata={"client_ip": client_ip, "limit_type": "burst"},
            )

        async with self.hourly_lock:
            now = time.monotonic()
            count, window_start = self.hourly_counts.get(client_ip, (0, now))

            if now - window_start >= 3600:
                self.hourly_counts[client_ip] = (1, now)
            else:
                if count >= self.hourly_limit:
                    return GuardrailResult(
                        passed=False,
                        reason="Hourly request limit exceeded.",
                        status_code=429,
                        metadata={"client_ip": client_ip, "limit_type": "hourly"},
                    )
                self.hourly_counts[client_ip] = (count + 1, window_start)

        return GuardrailResult(passed=True)
