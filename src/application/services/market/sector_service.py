import logging
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from shared.base_service import BaseService
from shared.constants import SECTOR_TTL_HOURS
from shared.ports.cache_port import CachePort
from shared.ports.company_port import CompanyPort
from shared.ports.market_data_port import MarketDataPort
from shared.utils.cache_keys import make_cache_key

logger = logging.getLogger(__name__)

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


class SectorService(BaseService):
    def __init__(self, cache: CachePort, company_port: CompanyPort, market_data: MarketDataPort) -> None:
        super().__init__("sector_service", cache, market_data)
        self._company = company_port

    def _get_tickers_in_sector(self, sector: str) -> list[str]:
        try:
            companies = self._company.get_overview("VNINDEX")
            if companies is None or getattr(companies, "empty", False):
                return []
            if "sector" in companies.columns:
                mask = companies["sector"].str.lower().str.contains(sector.lower(), na=False)
                return companies[mask]["ticker"].tolist() if "ticker" in companies.columns else []
            if "industry" in companies.columns:
                mask = companies["industry"].str.lower().str.contains(sector.lower(), na=False)
                return companies[mask]["ticker"].tolist() if "ticker" in companies.columns else []
            return []
        except Exception as e:
            logger.warning("Cannot query companies by sector '%s': %s", sector, e)
            return []

    def _get_performance(self, ticker: str, start_date: str, end_date: str) -> dict[str, Any] | None:
        try:
            if self._market_data is None:
                return None
            result = self._market_data.get_price_data(ticker, start_date, end_date)
            if result is None or "error" in result or not result.get("data"):
                return None
            data = result["data"]
            if len(data) < 2:
                return None
            first = float(data[0]["close"])
            last = float(data[-1]["close"])
            perf_pct = ((last - first) / first) * 100 if first else 0.0
            avg_volume = mean([int(r["volume"]) for r in data]) if data else 0
            return {"ticker": ticker, "first_price": first, "last_price": last, "performance_pct": round(perf_pct, 2), "avg_volume": int(avg_volume)}
        except Exception:
            return None

    def handle_query(self, sector: str, metric: str = "performance", timeframe: str = "1w") -> dict[str, Any]:
        if not sector:
            return {"error": "Missing sector parameter"}
        try:
            cache_key = make_cache_key("sector", sector, metric, timeframe)
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached  # type: ignore
            tickers = self._get_tickers_in_sector(sector)
            if not tickers:
                return {"sector": sector, "error": "Sector data unavailable", "suggested_tickers": []}
            start_date, end_date = _resolve_timeframe(timeframe)
            performances = []
            for ticker in tickers:
                perf = self._get_performance(ticker, start_date, end_date)
                if perf:
                    performances.append(perf)
            if metric == "volume":
                performances.sort(key=lambda x: x.get("avg_volume", 0), reverse=True)
            else:
                performances.sort(key=lambda x: x.get("performance_pct", 0), reverse=True)
            ranked = [{"rank": i + 1, "ticker": p["ticker"], "performance_pct": p.get("performance_pct"), "avg_volume": p.get("avg_volume")} for i, p in enumerate(performances)]
            result = {"sector": sector, "metric": metric, "timeframe": timeframe, "ranked_tickers": ranked, "total_tickers": len(performances)}
            self._cache.set(cache_key, result, ttl_hours=SECTOR_TTL_HOURS)
            return result
        except Exception as e:
            logger.error("Sector query failed: %s", e)
            return {"error": "Sector data unavailable", "suggested_tickers": []}


def handle_sector_query(sector: str, metric: str = "performance", timeframe: str = "1w") -> dict[str, Any]:
    from shared.service_registry import get_service
    svc = get_service("sector")
    if svc is None:
        raise RuntimeError("Service 'sector' not initialized — call init_deps()")
    return svc.handle_query(sector=sector, metric=metric, timeframe=timeframe)
