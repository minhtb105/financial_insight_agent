"""Shim for backward compat — delegates to MarketDataPort via service registry.

Strict hexagon: shared layer should not import infrastructure, but this shim exists only for legacy tests that patch shared.price_data.get_price_data.
Production code now uses MarketDataPort directly via BaseService.
"""

from typing import Any

from shared.service_registry import get_service


def get_price_data(
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
    days: int | None = None,
    cache_namespace: str = "price",
    ttl_hours: float = 0.5,
) -> dict[str, Any]:
    # Try to use market_data port via registry if available
    svc = get_service("price")
    if svc is not None:
        # Use the service's market_data if available, otherwise fallback
        try:
            if hasattr(svc, "_market_data") and svc._market_data is not None:
                # Handle days param
                if not start_date and days:
                    from datetime import datetime, timedelta, timezone
                    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
                return svc._market_data.get_price_data(ticker, start_date or "", end_date or "")
        except Exception:
            pass
    return {"error": "Market data unavailable — service not initialized"}
