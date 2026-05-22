from typing import Any
from statistics import mean
from datetime import datetime, timedelta, timezone
from shared.constants import SECTOR_TTL_HOURS
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.observability import get_logger
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

logger = get_logger(__name__)

_TIMEFRAME_DAYS = {
    "1d": 1,
    "5d": 5,
    "1w": 7,
    "2w": 14,
    "1m": 30,
    "3m": 90,
}


def _resolve_timeframe(timeframe: str) -> tuple[str, str]:
    days = _TIMEFRAME_DAYS.get(timeframe, 30)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _get_tickers_in_sector(sector: str) -> list[str]:
    try:
        client = VNStockClient(ticker="VNINDEX")
        companies = client.company.overview()
        if companies is None or companies.empty:
            return []
        if "sector" in companies.columns:
            mask = companies["sector"].str.lower().str.contains(sector.lower(), na=False)
            return companies[mask]["ticker"].tolist() if "ticker" in companies.columns else []
        if "industry" in companies.columns:
            mask = companies["industry"].str.lower().str.contains(sector.lower(), na=False)
            return companies[mask]["ticker"].tolist() if "ticker" in companies.columns else []
        if "company_code" in companies.columns:
            col = "sector" if "sector" in companies.columns else ("industry" if "industry" in companies.columns else None)
            if col:
                mask = companies[col].str.lower().str.contains(sector.lower(), na=False)
                return companies[mask]["company_code"].tolist()
            return []
        return []
    except Exception as e:
        logger.warning(f"Cannot query companies by sector '{sector}': {e}")
        return []


def _get_performance(ticker: str, start_date: str, end_date: str) -> dict[str, Any] | None:
    try:
        client = VNStockClient(ticker=ticker)
        data = client.fetch_trading_data(start=start_date, end=end_date, interval="1d")
        if data is None or data.empty or len(data) < 2:
            return None
        first = float(data.iloc[0]["close"])
        last = float(data.iloc[-1]["close"])
        perf_pct = ((last - first) / first) * 100 if first else 0.0
        avg_volume = mean([int(r["volume"]) for _, r in data.iterrows()]) if len(data) > 0 else 0
        return {
            "ticker": ticker,
            "first_price": first,
            "last_price": last,
            "performance_pct": round(perf_pct, 2),
            "avg_volume": int(avg_volume),
        }
    except Exception:
        return None


def handle_sector_query(
    sector: str,
    metric: str = "performance",
    timeframe: str = "1w",
) -> dict[str, Any]:
    if not sector:
        return {"error": "Missing sector parameter"}

    try:
        cache = get_cache_manager()
        cache_key = make_cache_key("sector", sector, metric, timeframe)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        tickers = _get_tickers_in_sector(sector)

        if not tickers:
            return {
                "sector": sector,
                "error": "Sector data unavailable",
                "suggested_tickers": [],
            }

        start_date, end_date = _resolve_timeframe(timeframe)
        performances = []
        for ticker in tickers:
            perf = _get_performance(ticker, start_date, end_date)
            if perf:
                performances.append(perf)

        if metric == "volume":
            performances.sort(key=lambda x: x.get("avg_volume", 0), reverse=True)
        else:
            performances.sort(key=lambda x: x.get("performance_pct", 0), reverse=True)

        ranked = [
            {
                "rank": i + 1,
                "ticker": p["ticker"],
                "performance_pct": p.get("performance_pct"),
                "avg_volume": p.get("avg_volume"),
            }
            for i, p in enumerate(performances)
        ]

        result = {
            "sector": sector,
            "metric": metric,
            "timeframe": timeframe,
            "ranked_tickers": ranked,
            "total_tickers": len(performances),
        }

        if cache:
            cache.set(cache_key, result, ttl_hours=SECTOR_TTL_HOURS)
        return result

    except Exception as e:
        logger.error(f"Sector query failed: {e}")
        return {"error": "Sector data unavailable", "suggested_tickers": []}
