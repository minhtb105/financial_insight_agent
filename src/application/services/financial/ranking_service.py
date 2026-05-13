from typing import Dict, Any, List, Optional
import pandas as pd
from shared.utils.time_processor import TimeProcessor
from shared.utils.calculations import calculate_volatility, calculate_std_dev
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_RANKING_TTL_HOURS = 0.5


def _cache() -> Optional[Any]:
    return get_cache_manager()


def handle_ranking_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    if not tickers or len(tickers) < 2:
        return {"error": "Need at least 2 tickers for ranking"}

    requested_field = parsed.get("requested_field", "close")
    aggregate = parsed.get("aggregate", "max")

    try:
        results = {}

        time_processor = TimeProcessor()
        time_params = time_processor.process_time_params(parsed)
        start_date = time_params["start_date"]
        end_date = time_params["end_date"]

        all_data = {}
        for ticker in tickers:
            try:
                data = get_price_data(ticker, start_date, end_date)
                if data:
                    all_data[ticker] = data
            except Exception as e:
                all_data[ticker] = {"error": str(e)}

        ranking_results = perform_ranking(all_data, requested_field, aggregate)

        results["ranking"] = ranking_results
        results["tickers"] = tickers
        results["requested_field"] = requested_field
        results["aggregate"] = aggregate
        results["time_range"] = {
            "start_date": start_date,
            "end_date": end_date
        }

        return results

    except Exception as e:
        return {"error": str(e)}


def get_price_data(
    ticker: str,
    start_date: str = None,
    end_date: str = None
) -> Dict[str, Any]:
    try:
        cache = _cache()
        cache_key = make_cache_key("ranking_price", ticker, start_date, end_date, interval="1d")
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        client = VNStockClient(ticker=ticker)

        data = client.fetch_trading_data(
            start=start_date,
            end=end_date,
            interval="1d"
        )

        if data is None or data.empty:
            return {"error": "No data available"}

        price_data = []
        for _, row in data.iterrows():
            price_data.append({
                "date": row["time"].strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"])
            })

        result = {
            "ticker": ticker,
            "data": price_data,
            "start_date": start_date,
            "end_date": end_date
        }
        if cache:
            cache.set(cache_key, result, ttl_hours=_RANKING_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}


def perform_ranking(
    all_data: Dict[str, Any],
    field: str,
    aggregate: str
) -> Dict[str, Any]:
    ranking = {}

    ticker_stats = {}
    for ticker, data in all_data.items():
        if "error" in data:
            ticker_stats[ticker] = {"error": data["error"]}
            continue

        values = [item[field] for item in data["data"] if field in item]
        if values:
            if aggregate == "max":
                stat_value = max(values)
            elif aggregate == "min":
                stat_value = min(values)
            elif aggregate == "mean":
                stat_value = sum(values) / len(values)
            elif aggregate == "latest":
                stat_value = values[-1]
            else:
                stat_value = max(values)

            ticker_stats[ticker] = {
                "value": stat_value,
                "count": len(values),
                "data_points": values
            }

    valid_stats = {k: v for k, v in ticker_stats.items() if "error" not in v}

    if not valid_stats:
        return {"error": "No valid data for ranking"}

    sorted_tickers = sorted(
        valid_stats.items(),
        key=lambda x: x[1]["value"],
        reverse=(aggregate != "min")
    )

    ranking_list = []
    for i, (ticker, stats) in enumerate(sorted_tickers, 1):
        ranking_list.append({
            "rank": i,
            "ticker": ticker,
            "value": stats["value"],
            "data_points": stats["count"]
        })

    top_performer = ranking_list[0] if ranking_list else None
    bottom_performer = ranking_list[-1] if ranking_list else None

    values = [stats["value"] for stats in valid_stats.values()]
    stats_summary = {
        "mean": sum(values) / len(values) if values else 0,
        "median": sorted(values)[len(values) // 2] if values else 0,
        "std_dev": calculate_std_dev(values) if values else 0,
        "range": (max(values) - min(values)) if values else 0
    }

    ranking = {
        "ranking_list": ranking_list,
        "top_performer": top_performer,
        "bottom_performer": bottom_performer,
        "total_tickers": len(valid_stats),
        "valid_tickers": list(valid_stats.keys()),
        "statistics": stats_summary,
        "field": field,
        "aggregate": aggregate
    }

    return ranking





def rank_performance(tickers: List[str], days: int = 30, metric: str = "performance") -> Dict[str, Any]:
    try:
        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data

        performance_data = {}
        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data or not ticker_data["data"]:
                continue

            price_data = ticker_data["data"]
            if len(price_data) < 2:
                continue

            if metric == "performance":
                first_price = price_data[0]["close"]
                last_price = price_data[-1]["close"]
                performance = ((last_price - first_price) / first_price) * 100
                performance_data[ticker] = performance

            elif metric == "volatility":
                volatility = calculate_volatility(price_data)
                performance_data[ticker] = volatility

            elif metric == "volume":
                volumes = [item["volume"] for item in price_data]
                avg_volume = sum(volumes) / len(volumes) if volumes else 0
                performance_data[ticker] = avg_volume

        if metric == "performance":
            sorted_tickers = sorted(
                performance_data.items(),
                key=lambda x: x[1],
                reverse=True
            )
        elif metric == "volatility":
            sorted_tickers = sorted(
                performance_data.items(),
                key=lambda x: x[1],
                reverse=False
            )
        else:
            sorted_tickers = sorted(
                performance_data.items(),
                key=lambda x: x[1],
                reverse=True
            )

        ranking_list = []
        for i, (ticker, value) in enumerate(sorted_tickers, 1):
            ranking_list.append({
                "rank": i,
                "ticker": ticker,
                "value": value,
                "metric": metric
            })

        return {
            "ranking": ranking_list,
            "metric": metric,
            "analysis_period": f"{days} days",
            "total_tickers": len(ranking_list),
            "top_performer": ranking_list[0] if ranking_list else None,
            "bottom_performer": ranking_list[-1] if ranking_list else None
        }

    except Exception as e:
        return {"error": str(e)}


def rank_by_indicator(
    tickers: List[str],
    indicator: str,
    period: int = 14,
    days: int = 30
) -> Dict[str, Any]:
    try:
        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data

        indicator_data = {}
        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data or not ticker_data["data"]:
                continue

            price_data = ticker_data["data"]
            if len(price_data) < period:
                continue

            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)

            if indicator == "rsi":
                rsi_value = calculate_rsi_value(df, period)
                if rsi_value is not None:
                    indicator_data[ticker] = rsi_value

            elif indicator == "macd":
                macd_value = calculate_macd_value(df)
                if macd_value is not None:
                    indicator_data[ticker] = macd_value

        sorted_tickers = sorted(
            indicator_data.items(),
            key=lambda x: x[1],
            reverse=True
        )

        ranking_list = []
        for i, (ticker, value) in enumerate(sorted_tickers, 1):
            ranking_list.append({
                "rank": i,
                "ticker": ticker,
                "value": value,
                "indicator": indicator,
                "period": period
            })

        return {
            "ranking": ranking_list,
            "indicator": indicator,
            "period": period,
            "analysis_period": f"{days} days",
            "total_tickers": len(ranking_list),
            "top_performer": ranking_list[0] if ranking_list else None,
            "bottom_performer": ranking_list[-1] if ranking_list else None
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_rsi_value(data: pd.DataFrame, period: int = 14) -> float:
    if len(data) < period + 1:
        return None

    close_prices = data['close'].astype(float)

    delta = close_prices.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None


def calculate_macd_value(data: pd.DataFrame) -> float:
    if len(data) < 26:
        return None

    close_prices = data['close'].astype(float)

    ema_fast = close_prices.ewm(span=12).mean()
    ema_slow = close_prices.ewm(span=26).mean()

    macd_line = ema_fast - ema_slow

    return float(macd_line.iloc[-1]) if pd.notna(macd_line.iloc[-1]) else None


def rank_by_volume(tickers: List[str], days: int = 30) -> Dict[str, Any]:
    return rank_performance(tickers, days, "volume")


def rank_by_volatility(tickers: List[str], days: int = 30) -> Dict[str, Any]:
    return rank_performance(tickers, days, "volatility")