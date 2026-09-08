"""Backward compat re-export — canonical TTLs live in shared.config."""

from shared.config import (
    COMPANY_TTL_HOURS,
    FORECAST_TTL_HOURS,
    INDICATOR_TTL_HOURS,
    NEWS_TTL_HOURS,
    PORTFOLIO_TTL_HOURS,
    PRICE_TTL_HOURS,
    RATIO_TTL_HOURS,
    SECTOR_TTL_HOURS,
)

__all__ = [
    "PRICE_TTL_HOURS",
    "INDICATOR_TTL_HOURS",
    "FORECAST_TTL_HOURS",
    "NEWS_TTL_HOURS",
    "COMPANY_TTL_HOURS",
    "RATIO_TTL_HOURS",
    "SECTOR_TTL_HOURS",
    "PORTFOLIO_TTL_HOURS",
]
