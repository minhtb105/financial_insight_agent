from typing import Dict, Any, List, Optional
from statistics import mean, stdev
from infrastructure.api_clients.vn_stock_client import VNStockClient
from shared.utils.time_processor import TimeProcessor
from infrastructure.observability import get_logger
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

logger = get_logger(__name__)

_FORECAST_TTL_HOURS = 1


def _cache() -> Optional[Any]:
    return get_cache_manager()


def handle_forecast_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    timeframe = parsed.get("timeframe", "1w")

    if not tickers:
        return {"error": "Missing tickers"}

    try:
        cache = _cache()
        results = {}

        for ticker in tickers:
            try:
                cache_key = make_cache_key("forecast", ticker, timeframe)
                cached = cache.get(cache_key) if cache else None
                if cached is not None:
                    results[ticker] = cached
                    continue

                client = VNStockClient(ticker=ticker)
                data = client.fetch_trading_data(start=None, end=None, interval="1d")

                if data is None or data.empty or len(data) < 20:
                    results[ticker] = {"error": "Insufficient historical data for forecast"}
                    continue

                close_prices = data["close"].astype(float).tolist()
                n = len(close_prices)
                sma_20 = mean(close_prices[-20:])
                recent_trend = (close_prices[-1] - close_prices[-5]) / close_prices[-5] if n >= 5 else 0.0
                volatility = stdev(close_prices[-20:]) if n >= 20 else 0.0

                last_price = close_prices[-1]
                projected_price = last_price * (1 + recent_trend)
                confidence_bound = volatility * 1.96

                forecast = {
                    "ticker": ticker,
                    "last_price": round(last_price, 2),
                    "projected_price": round(projected_price, 2),
                    "confidence_bounds": {
                        "lower": round(projected_price - confidence_bound, 2),
                        "upper": round(projected_price + confidence_bound, 2),
                    },
                    "volatility": round(volatility, 4),
                    "trend_pct": round(recent_trend * 100, 2),
                    "sma_20": round(sma_20, 2),
                    "data_points": n,
                    "timeframe": timeframe,
                }

                results[ticker] = forecast
                if cache:
                    cache.set(cache_key, forecast, ttl_hours=_FORECAST_TTL_HOURS)

            except Exception as e:
                logger.error(f"Forecast failed for {ticker}: {e}")
                results[ticker] = {"error": f"Insufficient historical data for forecast: {e}"}

        if not results:
            return {"error": "Insufficient historical data for forecast"}

        return {
            "forecasts": results,
            "model": "simple_moving_average",
            "timeframe": timeframe,
        }

    except Exception as e:
        logger.error(f"Forecast query failed: {e}")
        return {"error": f"Insufficient historical data for forecast: {e}"}