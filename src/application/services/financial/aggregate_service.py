from typing import Dict, Any, List, Optional
import pandas as pd
from shared.utils.time_processor import TimeProcessor
from shared.utils.calculations import calculate_volatility, calculate_std_dev
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_AGGREGATE_TTL_HOURS = 0.5


def _cache() -> Optional[Any]:
    return get_cache_manager()


def handle_aggregate_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    if not tickers or len(tickers) < 1:
        return {"error": "Need at least 1 ticker for aggregation"}

    requested_field = parsed.get("requested_field", "close")
    aggregate = parsed.get("aggregate", "mean")

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

        aggregate_results = perform_aggregation(all_data, requested_field, aggregate)

        results["aggregation"] = aggregate_results
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
        cache_key = make_cache_key("aggregate_price", ticker, start_date, end_date, interval="1d")
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
            cache.set(cache_key, result, ttl_hours=_AGGREGATE_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}


def perform_aggregation(
    all_data: Dict[str, Any],
    field: str,
    aggregate_func: str
) -> Dict[str, Any]:
    aggregation = {}

    all_values = []
    ticker_data = {}

    for ticker, data in all_data.items():
        if "error" in data:
            continue

        values = [item[field] for item in data["data"] if field in item]
        if values:
            ticker_data[ticker] = {
                "values": values,
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
            all_values.extend(values)

    if not all_values:
        return {"error": "No valid data for aggregation"}

    if aggregate_func == "mean":
        result_value = sum(all_values) / len(all_values)
    elif aggregate_func == "sum":
        result_value = sum(all_values)
    elif aggregate_func == "median":
        sorted_values = sorted(all_values)
        n = len(sorted_values)
        if n % 2 == 0:
            result_value = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            result_value = sorted_values[n//2]
    elif aggregate_func == "std":
        mean_val = sum(all_values) / len(all_values)
        variance = sum((x - mean_val) ** 2 for x in all_values) / len(all_values)
        result_value = variance ** 0.5
    elif aggregate_func == "min":
        result_value = min(all_values)
    elif aggregate_func == "max":
        result_value = max(all_values)
    else:
        result_value = sum(all_values) / len(all_values)

    overall_mean = sum(all_values) / len(all_values)
    overall_min = min(all_values)
    overall_max = max(all_values)
    overall_sum = sum(all_values)

    sorted_values = sorted(all_values)
    n = len(sorted_values)
    if n % 2 == 0:
        overall_median = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        overall_median = sorted_values[n//2]

    variance = sum((x - overall_mean) ** 2 for x in all_values) / len(all_values)
    overall_std = variance ** 0.5

    cv = (overall_std / overall_mean) * 100 if overall_mean != 0 else 0

    aggregation = {
        "result": {
            "function": aggregate_func,
            "value": result_value,
            "field": field
        },
        "overall_statistics": {
            "mean": overall_mean,
            "median": overall_median,
            "std_dev": overall_std,
            "min": overall_min,
            "max": overall_max,
            "sum": overall_sum,
            "coefficient_of_variation": cv,
            "total_data_points": len(all_values)
        },
        "ticker_breakdown": ticker_data,
        "valid_tickers": list(ticker_data.keys()),
        "total_tickers": len(ticker_data)
    }

    return aggregation


def calculate_correlation_matrix(tickers: List[str], field: str = "close", days: int = 30) -> Dict[str, Any]:
    try:
        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data

        correlation_data = {}
        dates = set()

        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data:
                continue

            values = {}
            for item in ticker_data["data"]:
                date = item["date"]
                if field in item:
                    values[date] = item[field]
                    dates.add(date)

            if values:
                correlation_data[ticker] = values

        if not correlation_data:
            return {"error": "No valid data for correlation calculation"}

        dates_list = sorted(list(dates))
        df_data = {}

        for ticker, values in correlation_data.items():
            df_data[ticker] = [values.get(date, None) for date in dates_list]

        df = pd.DataFrame(df_data, index=dates_list)

        correlation_matrix = df.corr()

        corr_dict = {}
        for ticker1 in tickers:
            if ticker1 in correlation_matrix.columns:
                corr_dict[ticker1] = {}
                for ticker2 in tickers:
                    if ticker2 in correlation_matrix.columns:
                        corr_value = correlation_matrix.loc[ticker1, ticker2]
                        if pd.notna(corr_value):
                            corr_dict[ticker1][ticker2] = float(corr_value)

        return {
            "correlation_matrix": corr_dict,
            "field": field,
            "analysis_period": f"{days} days",
            "valid_tickers": list(correlation_data.keys()),
            "total_tickers": len(correlation_data)
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_portfolio_statistics(tickers: List[str], weights: List[float], days: int = 30) -> Dict[str, Any]:
    try:
        if len(tickers) != len(weights):
            return {"error": "Number of tickers must match number of weights"}

        if abs(sum(weights) - 1.0) > 1e-6:
            return {"error": "Weights must sum to 1"}

        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data

        ticker_stats = {}
        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data or not ticker_data["data"]:
                continue

            price_data = ticker_data["data"]
            if len(price_data) < 2:
                continue

            returns = []
            for i in range(1, len(price_data)):
                prev_price = price_data[i-1]["close"]
                curr_price = price_data[i]["close"]
                if prev_price != 0:
                    return_pct = (curr_price - prev_price) / prev_price
                    returns.append(return_pct)

            if not returns:
                continue

            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5

            ticker_stats[ticker] = {
                "mean_return": mean_return,
                "std_dev": std_dev,
                "variance": variance,
                "returns": returns
            }

        if not ticker_stats:
            return {"error": "No valid data for portfolio calculation"}

        portfolio_mean = 0
        portfolio_variance = 0

        valid_tickers = list(ticker_stats.keys())
        valid_weights = [weights[tickers.index(ticker)] for ticker in valid_tickers]

        for i, ticker in enumerate(valid_tickers):
            portfolio_mean += valid_weights[i] * ticker_stats[ticker]["mean_return"]

        for i, ticker in enumerate(valid_tickers):
            portfolio_variance += (valid_weights[i] ** 2) * ticker_stats[ticker]["variance"]

        portfolio_std_dev = portfolio_variance ** 0.5

        sharpe_ratio = portfolio_mean / portfolio_std_dev if portfolio_std_dev != 0 else 0

        return {
            "portfolio_statistics": {
                "mean_return": portfolio_mean,
                "std_dev": portfolio_std_dev,
                "variance": portfolio_variance,
                "sharpe_ratio": sharpe_ratio
            },
            "individual_statistics": ticker_stats,
            "weights": dict(zip(valid_tickers, valid_weights)),
            "valid_tickers": valid_tickers,
            "analysis_period": f"{days} days"
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_sector_statistics(tickers: List[str], sector_map: Dict[str, str], days: int = 30) -> Dict[str, Any]:
    try:
        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data

        sector_data = {}
        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data or not ticker_data["data"]:
                continue

            sector = sector_map.get(ticker, "Unknown")
            if sector not in sector_data:
                sector_data[sector] = {}

            price_data = ticker_data["data"]
            if len(price_data) >= 2:
                first_price = price_data[0]["close"]
                last_price = price_data[-1]["close"]
                performance = ((last_price - first_price) / first_price) * 100

                sector_data[sector][ticker] = {
                    "performance": performance,
                    "first_price": first_price,
                    "last_price": last_price
                }

        sector_stats = {}
        for sector, tickers_data in sector_data.items():
            if not tickers_data:
                continue

            performances = [data["performance"] for data in tickers_data.values()]

            sector_stats[sector] = {
                "tickers": list(tickers_data.keys()),
                "mean_performance": sum(performances) / len(performances),
                "median_performance": sorted(performances)[len(performances) // 2],
                "std_dev": calculate_std_dev(performances) if performances else 0,
                "min_performance": min(performances),
                "max_performance": max(performances),
                "total_tickers": len(tickers_data)
            }

        sorted_sectors = sorted(
            sector_stats.items(),
            key=lambda x: x[1]["mean_performance"],
            reverse=True
        )

        return {
            "sector_statistics": dict(sorted_sectors),
            "analysis_period": f"{days} days",
            "total_sectors": len(sector_stats)
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_performance_metrics(tickers: List[str], days: int = 30) -> Dict[str, Any]:
    try:
        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data

        metrics = {}
        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data or not ticker_data["data"]:
                continue

            price_data = ticker_data["data"]
            if len(price_data) < 2:
                continue

            first_price = price_data[0]["close"]
            last_price = price_data[-1]["close"]
            performance = ((last_price - first_price) / first_price) * 100

            volatility = calculate_volatility(price_data)

            max_drawdown = calculate_max_drawdown(price_data)

            returns = []
            for i in range(1, len(price_data)):
                prev_price = price_data[i-1]["close"]
                curr_price = price_data[i]["close"]
                if prev_price != 0:
                    return_pct = (curr_price - prev_price) / prev_price
                    returns.append(return_pct)

            if returns:
                mean_return = sum(returns) / len(returns)
                std_dev = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = mean_return / std_dev if std_dev != 0 else 0
            else:
                sharpe_ratio = 0

            metrics[ticker] = {
                "performance": performance,
                "volatility": volatility,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "first_price": first_price,
                "last_price": last_price,
                "data_points": len(price_data)
            }

        if metrics:
            performances = [m["performance"] for m in metrics.values()]
            volatilities = [m["volatility"] for m in metrics.values()]

            overall_stats = {
                "mean_performance": sum(performances) / len(performances),
                "mean_volatility": sum(volatilities) / len(volatilities),
                "best_performer": max(metrics.items(), key=lambda x: x[1]["performance"]),
                "worst_performer": min(metrics.items(), key=lambda x: x[1]["performance"]),
                "lowest_volatility": min(metrics.items(), key=lambda x: x[1]["volatility"]),
                "highest_volatility": max(metrics.items(), key=lambda x: x[1]["volatility"])
            }
        else:
            overall_stats = {}

        return {
            "individual_metrics": metrics,
            "overall_statistics": overall_stats,
            "analysis_period": f"{days} days",
            "total_tickers": len(metrics)
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_max_drawdown(price_data: List[Dict[str, Any]]) -> float:
    if len(price_data) < 2:
        return 0.0

    prices = [item["close"] for item in price_data]
    max_price = prices[0]
    max_drawdown = 0

    for price in prices:
        if price > max_price:
            max_price = price
        else:
            drawdown = ((max_price - price) / max_price) * 100
            max_drawdown = max(max_drawdown, drawdown)

    return max_drawdown


