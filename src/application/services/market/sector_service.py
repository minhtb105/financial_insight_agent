from typing import Dict, Any, List, Optional
from statistics import mean
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.observability import get_logger
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

logger = get_logger(__name__)

_SECTOR_TTL_HOURS = 2


def _cache() -> Optional[Any]:
    return get_cache_manager()


def _get_tickers_in_sector(sector: str) -> List[str]:
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
            mask = companies["sector"].str.lower().str.contains(sector.lower(), na=False) if "sector" in companies.columns else []
            return companies[mask]["company_code"].tolist() if not mask.empty else []
        return []
    except Exception as e:
        logger.warning(f"Cannot query companies by sector '{sector}': {e}")
        return []


def _get_performance(ticker: str) -> Optional[Dict[str, Any]]:
    try:
        client = VNStockClient(ticker=ticker)
        data = client.fetch_trading_data(start=None, end=None, interval="1d")
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


def handle_sector_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    sector = parsed.get("sector", "")
    metric = parsed.get("metric", "performance")
    timeframe = parsed.get("timeframe", "1w")

    if not sector:
        return {"error": "Missing sector parameter"}

    try:
        cache = _cache()
        cache_key = make_cache_key("sector", sector, metric, timeframe)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        tickers = _get_tickers_in_sector(sector)

        if not tickers:
            result = {
                "sector": sector,
                "error": "Sector data unavailable",
                "suggested_tickers": [],
            }
            return result

        performances = []
        for ticker in tickers:
            perf = _get_performance(ticker)
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
            cache.set(cache_key, result, ttl_hours=_SECTOR_TTL_HOURS)
        return result

    except Exception as e:
        logger.error(f"Sector query failed: {e}")
        return {"error": "Sector data unavailable", "suggested_tickers": []}