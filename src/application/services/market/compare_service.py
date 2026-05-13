from typing import Dict, Any, List, Optional
from shared.utils.time_processor import TimeProcessor
from shared.utils.calculations import calculate_volatility
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_COMPARE_TTL_HOURS = 0.5


def _cache() -> Optional[Any]:
    return get_cache_manager()


def handle_compare_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    compare_with = parsed.get("compare_with") or []

    if not tickers or not compare_with:
        return {"error": "Missing tickers or compare_with parameters"}

    requested_field = parsed.get("requested_field", "close")

    try:
        results = {}

        time_processor = TimeProcessor()
        time_params = time_processor.process_time_params(parsed)
        start_date = time_params["start_date"]
        end_date = time_params["end_date"]

        main_data = {}
        for ticker in tickers:
            try:
                data = get_price_data(ticker, start_date, end_date)
                if data:
                    main_data[ticker] = data
            except Exception as e:
                main_data[ticker] = {"error": str(e)}

        compare_data = {}
        for ticker in compare_with:
            try:
                data = get_price_data(ticker, start_date, end_date)
                if data:
                    compare_data[ticker] = data
            except Exception as e:
                compare_data[ticker] = {"error": str(e)}

        comparison_results = perform_comparison(
            main_data, compare_data, requested_field
        )

        results["comparison"] = comparison_results
        results["main_tickers"] = tickers
        results["compare_tickers"] = compare_with
        results["requested_field"] = requested_field
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
        cache_key = make_cache_key("compare_price", ticker, start_date, end_date, interval="1d")
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
            cache.set(cache_key, result, ttl_hours=_COMPARE_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}


def perform_comparison(
    main_data: Dict[str, Any],
    compare_data: Dict[str, Any],
    field: str
) -> Dict[str, Any]:
    comparison = {}

    main_stats = {}
    for ticker, data in main_data.items():
        if "error" in data:
            main_stats[ticker] = {"error": data["error"]}
            continue

        values = [item[field] for item in data["data"] if field in item]
        if values:
            main_stats[ticker] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1] if values else None,
                "count": len(values)
            }

    compare_stats = {}
    for ticker, data in compare_data.items():
        if "error" in data:
            compare_stats[ticker] = {"error": data["error"]}
            continue

        values = [item[field] for item in data["data"] if field in item]
        if values:
            compare_stats[ticker] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1] if values else None,
                "count": len(values)
            }

    main_overall = calculate_overall_stats(main_stats, field)
    compare_overall = calculate_overall_stats(compare_stats, field)

    percentage_diff = calculate_percentage_difference(main_overall, compare_overall)

    comparison = {
        "main_tickers_stats": main_stats,
        "compare_tickers_stats": compare_stats,
        "main_overall": main_overall,
        "compare_overall": compare_overall,
        "percentage_difference": percentage_diff,
        "field": field
    }

    return comparison


def calculate_overall_stats(stats: Dict[str, Any], field: str) -> Dict[str, Any]:
    valid_stats = {k: v for k, v in stats.items() if "error" not in v}

    if not valid_stats:
        return {"error": "No valid data for calculation"}

    total_mean = sum(stat["mean"] for stat in valid_stats.values())
    overall_mean = total_mean / len(valid_stats)

    all_mins = [stat["min"] for stat in valid_stats.values()]
    all_maxs = [stat["max"] for stat in valid_stats.values()]

    overall_min = min(all_mins)
    overall_max = max(all_maxs)

    latest_values = [stat["latest"] for stat in valid_stats.values() if stat["latest"] is not None]
    latest_mean = sum(latest_values) / len(latest_values) if latest_values else None

    return {
        "mean": overall_mean,
        "min": overall_min,
        "max": overall_max,
        "latest_mean": latest_mean,
        "tickers_count": len(valid_stats),
        "total_data_points": sum(stat["count"] for stat in valid_stats.values())
    }


def calculate_percentage_difference(main_stats: Dict[str, Any], compare_stats: Dict[str, Any]) -> Dict[str, Any]:
    if "error" in main_stats or "error" in compare_stats:
        return {"error": "Cannot calculate percentage difference with invalid data"}

    diff = {}

    for metric in ["mean", "min", "max", "latest_mean"]:
        if metric in main_stats and metric in compare_stats:
            main_val = main_stats[metric]
            compare_val = compare_stats[metric]

            if compare_val != 0:
                percentage = ((main_val - compare_val) / compare_val) * 100
                diff[metric] = {
                    "main": main_val,
                    "compare": compare_val,
                    "difference": main_val - compare_val,
                    "percentage": percentage
                }

    return diff


def compare_performance(tickers: List[str], compare_with: List[str], days: int = 30) -> Dict[str, Any]:
    try:
        main_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                main_data[ticker] = data

        compare_data = {}
        for ticker in compare_with:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                compare_data[ticker] = data

        main_performance = calculate_performance_metrics(main_data, days)
        compare_performance = calculate_performance_metrics(compare_data, days)

        relative_performance = calculate_relative_performance(main_performance, compare_performance)

        return {
            "main_group": main_performance,
            "compare_group": compare_performance,
            "relative_performance": relative_performance,
            "analysis_period": f"{days} days"
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_performance_metrics(data: Dict[str, Any], days: int) -> Dict[str, Any]:
    if not data:
        return {"error": "No data available"}

    performances = {}
    for ticker, ticker_data in data.items():
        if "data" not in ticker_data or not ticker_data["data"]:
            continue

        price_data = ticker_data["data"]
        if len(price_data) < 2:
            continue

        first_price = price_data[0]["close"]
        last_price = price_data[-1]["close"]

        performance = ((last_price - first_price) / first_price) * 100

        performances[ticker] = {
            "first_price": first_price,
            "last_price": last_price,
            "performance": performance,
            "volatility": calculate_volatility(price_data)
        }

    if not performances:
        return {"error": "No valid performance data"}

    avg_performance = sum(p["performance"] for p in performances.values()) / len(performances)
    max_performance = max(p["performance"] for p in performances.values())
    min_performance = min(p["performance"] for p in performances.values())

    return {
        "individual_performances": performances,
        "average_performance": avg_performance,
        "max_performance": max_performance,
        "min_performance": min_performance,
        "volatility": sum(p["volatility"] for p in performances.values()) / len(performances),
        "tickers_count": len(performances)
    }


def calculate_relative_performance(main_perf: Dict[str, Any], compare_perf: Dict[str, Any]) -> Dict[str, Any]:
    if "error" in main_perf or "error" in compare_perf:
        return {"error": "Cannot calculate relative performance with invalid data"}

    main_avg = main_perf.get("average_performance", 0)
    compare_avg = compare_perf.get("average_performance", 0)

    if compare_avg != 0:
        relative_perf = ((main_avg - compare_avg) / abs(compare_avg)) * 100
    else:
        relative_perf = 0

    return {
        "main_average": main_avg,
        "compare_average": compare_avg,
        "relative_performance": relative_perf,
        "outperformance": main_avg > compare_avg,
        "underperformance": main_avg < compare_avg
    }