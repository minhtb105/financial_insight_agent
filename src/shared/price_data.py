import os
import re
from typing import Any
from datetime import datetime, timedelta, timezone

from domain.entities.time_range import validate_ticker_list
from infrastructure.api_clients.vn_stock_client import VNStockClient
from shared.constants import PRICE_TTL_HOURS
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _cache() -> Any | None:
    try:
        return get_cache_manager()
    except Exception:
        return None


def _validate_date(date_str: str, label: str) -> str | None:
    if date_str and not _DATE_PATTERN.match(date_str):
        return f"Invalid {label}: {date_str} (expected YYYY-MM-DD)"
    return None


def get_price_data(
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
    days: int | None = None,
    cache_namespace: str = "price",
    ttl_hours: float = PRICE_TTL_HOURS,
) -> dict[str, Any]:
    try:
        validate_ticker_list([ticker])
    except ValueError as e:
        return {"error": str(e)}

    try:
        if not start_date and days:
            if days < 0:
                return {"error": "days must be non-negative"}
            start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not start_date:
            return {"error": "start_date or days is required"}

        date_err = _validate_date(start_date, "start_date")
        if date_err:
            return {"error": date_err}
        date_err = _validate_date(end_date, "end_date")
        if date_err:
            return {"error": date_err}

        cache = _cache()
        cache_key = make_cache_key(cache_namespace, ticker, start_date, end_date, interval="1d")
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        client = VNStockClient(ticker=ticker)

        data = client.fetch_trading_data(start=start_date, end=end_date, interval="1d")

        if data is None or data.empty:
            return {"error": "No data available"}

        price_data = []
        for _, row in data.iterrows():
            price_data.append(
                {
                    "date": row["date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
            )

        result = {
            "ticker": ticker,
            "data": price_data,
            "start_date": start_date,
            "end_date": end_date,
        }
        if cache and "error" not in result:
            cache.set(cache_key, result, ttl_hours=ttl_hours)
        return result

    except Exception as e:
        return {"error": str(e)}
