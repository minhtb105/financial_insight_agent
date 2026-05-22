import contextlib
import logging
import math
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


_INTERVAL_ANNUAL_FACTORS: dict[str, int] = {
    "daily": 252,
    "weekly": 52,
    "monthly": 12,
    "intraday": 252,
}


def _detect_interval(price_data: list[dict[str, Any]]) -> str:
    if len(price_data) < 2:
        return "daily"

    dates = []
    for d in price_data:
        date_val = d.get("date") or d.get("timestamp") or d.get("time")
        if not date_val:
            continue
        with contextlib.suppress(ValueError, TypeError):
            dates.append(datetime.fromisoformat(str(date_val).replace("Z", "+00:00")))
    if len(dates) >= 4:
        diffs = [(dates[i] - dates[i - 1]).total_seconds() for i in range(1, len(dates))]
        median_diff = sorted(diffs)[len(diffs) // 2]
        if median_diff >= 3600 * 24 * 6:
            return "weekly"
        if median_diff >= 3600 * 24 * 20:
            return "monthly"
    return "daily"


def calculate_volatility(
    price_data: list[dict[str, Any]],
    annual_factor: int | None = None,
    interval: str | None = None,
) -> float:
    if len(price_data) < 2:
        return 0.0

    returns = []
    for i in range(1, len(price_data)):
        prev = price_data[i - 1].get("close")
        curr = price_data[i].get("close")
        if prev is None or curr is None:
            continue
        if prev != 0 and not math.isnan(prev) and not math.isnan(curr):
            return_pct = (curr - prev) / prev
            returns.append(return_pct)
        elif prev == 0 and curr is not None:
            logger.warning(
                "Previous price is zero for volatility calculation — skipping data point"
            )

    if len(returns) < 2:
        return 0.0

    if annual_factor is None:
        if interval is not None and interval in _INTERVAL_ANNUAL_FACTORS:
            annual_factor = _INTERVAL_ANNUAL_FACTORS[interval]
        else:
            detected = _detect_interval(price_data)
            annual_factor = _INTERVAL_ANNUAL_FACTORS.get(detected, 252)

    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    volatility = (variance**0.5) * (annual_factor**0.5)

    return volatility * 100


def calculate_std_dev(values: list[float]) -> float:
    clean = [v for v in values if not math.isnan(v)]
    if len(clean) < 2:
        return 0.0

    mean = sum(clean) / len(clean)
    variance = sum((v - mean) ** 2 for v in clean) / (len(clean) - 1)
    return variance**0.5
