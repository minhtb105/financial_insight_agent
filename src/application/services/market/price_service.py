from typing import Dict, Any, Optional
from datetime import datetime
from infrastructure.api_clients.vn_stock_client import VNStockClient
from shared.utils.time_processor import TimeProcessor
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_PRICE_TTL_HOURS = 0.5


def _cache() -> Optional[Any]:
    return get_cache_manager()


def handle_price_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    requested_field = parsed.get("requested_field", "close")

    try:
        results = {}

        cache = _cache()

        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)

                time_processor = TimeProcessor()
                time_params = time_processor.process_time_params(parsed)
                start_date = time_params["start_date"]
                end_date = time_params["end_date"]

                cache_key = make_cache_key("price", ticker, start_date, end_date, interval="1d", requested_field=requested_field)
                cached = cache.get(cache_key) if cache else None
                if cached is not None:
                    results[ticker] = cached
                    continue

                data = client.fetch_trading_data(
                    start=start_date,
                    end=end_date,
                    interval="1d"
                )

                if data is None or data.empty:
                    results[ticker] = {"error": "No data available"}
                    continue

                if requested_field == "ohlcv":
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": int(row["volume"])
                        })
                    results[ticker] = ticker_data

                elif requested_field == "open":
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "open": float(row["open"])
                        })
                    results[ticker] = ticker_data

                elif requested_field == "close":
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "close": float(row["close"])
                        })
                    results[ticker] = ticker_data

                elif requested_field == "volume":
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "volume": int(row["volume"])
                        })
                    results[ticker] = ticker_data

                else:
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "close": float(row["close"])
                        })
                    results[ticker] = ticker_data

                if cache and ticker_data:
                    cache.set(cache_key, ticker_data, ttl_hours=_PRICE_TTL_HOURS)

            except Exception as e:
                results[ticker] = {"error": str(e)}

        return results if results else {"error": "No valid data found"}

    except Exception as e:
        return {"error": str(e)}


def get_latest_price(ticker: str, field: str = "close") -> Dict[str, Any]:
    try:
        cache = _cache()
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = make_cache_key("latest_price", ticker, today, today, field=field)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        client = VNStockClient(ticker=ticker)

        data = client.fetch_trading_data(
            start=today,
            end=today,
            interval="1d"
        )

        if data is None or data.empty:
            return {"error": "No data available"}

        latest_row = data.iloc[-1]

        if field == "open":
            result = {"ticker": ticker, "date": today, "open": float(latest_row["open"])}
        elif field == "close":
            result = {"ticker": ticker, "date": today, "close": float(latest_row["close"])}
        elif field == "high":
            result = {"ticker": ticker, "date": today, "high": float(latest_row["high"])}
        elif field == "low":
            result = {"ticker": ticker, "date": today, "low": float(latest_row["low"])}
        elif field == "volume":
            result = {"ticker": ticker, "date": today, "volume": int(latest_row["volume"])}
        else:
            result = {"ticker": ticker, "date": today, "close": float(latest_row["close"])}

        if cache:
            cache.set(cache_key, result, ttl_hours=_PRICE_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}


def get_price_history(ticker: str, days: int = 30, field: str = "close") -> Dict[str, Any]:
    try:
        cache = _cache()
        end_date = datetime.now()
        start_date = end_date.replace(day=end_date.day - days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        cache_key = make_cache_key("price_history", ticker, start_str, end_str, days=days, field=field)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        client = VNStockClient(ticker=ticker)

        data = client.fetch_trading_data(
            start=start_str,
            end=end_str,
            interval="1d"
        )

        if data is None or data.empty:
            return {"error": "No data available"}

        history = []
        for _, row in data.iterrows():
            if field == "open":
                value = float(row["open"])
            elif field == "close":
                value = float(row["close"])
            elif field == "high":
                value = float(row["high"])
            elif field == "low":
                value = float(row["low"])
            elif field == "volume":
                value = int(row["volume"])
            else:
                value = float(row["close"])

            history.append({
                "date": row["time"].strftime("%Y-%m-%d"),
                field: value
            })

        result = {
            "ticker": ticker,
            "field": field,
            "days": days,
            "history": history
        }
        if cache:
            cache.set(cache_key, result, ttl_hours=_PRICE_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}