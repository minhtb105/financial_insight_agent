import logging

from .base import Guardrail, GuardrailResult
from .config import GuardrailConfig
from .rate_limiter import RateLimiter
from .content_filter import ContentFilter
from .query_validator import QuerySizeLimit, TickerValidator, PatternGuard
from infrastructure.observability.metrics.collector import get_metrics_collector

logger = logging.getLogger("guardrails")


class GuardrailPipeline:
    def __init__(self, config: GuardrailConfig | None = None):
        cfg = config or GuardrailConfig()
        self.guardrails: list[Guardrail] = [
            RateLimiter(cfg),
            QuerySizeLimit(cfg),
            ContentFilter(cfg),
            TickerValidator(cfg),
            PatternGuard(),
        ]

    def check(self, query: str, client_ip: str) -> GuardrailResult:
        for guardrail in self.guardrails:
            result = guardrail.validate(query, client_ip)
            if not result.passed:
                logger.warning(
                    "Guardrail '%s' blocked request from %s (len=%d): %s",
                    guardrail.name,
                    client_ip,
                    len(query),
                    result.reason,
                )
                metrics = get_metrics_collector()
                if metrics:
                    metrics.increment_counter(
                        "guardrail_blocks_total",
                        1,
                        {
                            "guardrail": guardrail.name,
                            "status_code": str(result.status_code),
                        },
                    )
                    metrics.increment_counter(
                        "guardrail_blocks_by_reason_total",
                        1,
                        {
                            "guardrail": guardrail.name,
                            "reason": result.metadata.get("type", "unknown"),
                        },
                    )
                return result
        return GuardrailResult(passed=True)
