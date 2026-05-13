import json
from typing import Dict, Any, List, Optional
import pandas as pd
from infrastructure.api_clients.vn_stock_client import VNStockClient
from shared.utils.time_processor import TimeProcessor
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_INDICATOR_TTL_HOURS = 0.5


def _cache() -> Optional[Any]:
    return get_cache_manager()


def handle_indicator_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    indicator_params = parsed.get("indicator_params") or {}
    requested_field = parsed.get("requested_field", "sma")

    try:
        cache = _cache()
        results = {}

        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)

                time_processor = TimeProcessor()
                time_params = time_processor.process_time_params(parsed)
                start_date = time_params["start_date"]
                end_date = time_params["end_date"]

                ip_str = json.dumps(indicator_params, sort_keys=True) if indicator_params else ""
                cache_key = make_cache_key("indicator", ticker, start_date, end_date, requested_field=requested_field, indicator_params=ip_str)
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

                ticker_results = {}

                if requested_field == "sma" or "sma" in indicator_params:
                    sma_periods = indicator_params.get("sma", [20])
                    for period in sma_periods:
                        sma_data = calculate_sma(data, period)
                        ticker_results[f"sma_{period}"] = sma_data

                if requested_field == "rsi" or "rsi" in indicator_params:
                    rsi_periods = indicator_params.get("rsi", [14])
                    for period in rsi_periods:
                        rsi_data = calculate_rsi(data, period)
                        ticker_results[f"rsi_{period}"] = rsi_data

                if requested_field == "macd" or "macd" in indicator_params:
                    macd_params = indicator_params.get("macd", [(12, 26)])
                    for fast, slow in macd_params:
                        macd_data = calculate_macd(data, fast, slow)
                        ticker_results[f"macd_{fast}_{slow}"] = macd_data

                results[ticker] = ticker_results
                if cache:
                    cache.set(cache_key, ticker_results, ttl_hours=_INDICATOR_TTL_HOURS)

            except Exception as e:
                results[ticker] = {"error": str(e)}

        return results if results else {"error": "No valid data found"}

    except Exception as e:
        return {"error": str(e)}


def calculate_sma(data: pd.DataFrame, period: int) -> List[Dict[str, Any]]:
    if len(data) < period:
        return []

    close_prices = data['close'].astype(float)
    sma_values = close_prices.rolling(window=period).mean()

    result = []
    for i, (date, sma) in enumerate(zip(data['time'], sma_values)):
        if pd.notna(sma):
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "sma": float(sma)
            })

    return result


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> List[Dict[str, Any]]:
    if len(data) < period + 1:
        return []

    close_prices = data['close'].astype(float)

    delta = close_prices.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    result = []
    for i, (date, rsi_val) in enumerate(zip(data['time'], rsi)):
        if pd.notna(rsi_val):
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "rsi": float(rsi_val)
            })

    return result


def calculate_macd(data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26) -> Dict[str, List[Dict[str, Any]]]:
    if len(data) < slow_period:
        return {"error": "Insufficient data for MACD calculation"}

    close_prices = data['close'].astype(float)

    ema_fast = close_prices.ewm(span=fast_period).mean()
    ema_slow = close_prices.ewm(span=slow_period).mean()

    macd_line = ema_fast - ema_slow

    signal_line = macd_line.ewm(span=9).mean()

    histogram = macd_line - signal_line

    macd_result = []
    signal_result = []
    histogram_result = []

    for i, date in enumerate(data['time']):
        if pd.notna(macd_line.iloc[i]):
            macd_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "macd": float(macd_line.iloc[i])
            })

        if pd.notna(signal_line.iloc[i]):
            signal_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "signal": float(signal_line.iloc[i])
            })

        if pd.notna(histogram.iloc[i]):
            histogram_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "histogram": float(histogram.iloc[i])
            })

    return {
        "macd_line": macd_result,
        "signal_line": signal_result,
        "histogram": histogram_result
    }


def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: float = 2) -> Dict[str, List[Dict[str, Any]]]:
    if len(data) < period:
        return {"error": "Insufficient data for Bollinger Bands calculation"}

    close_prices = data['close'].astype(float)

    middle_band = close_prices.rolling(window=period).mean()

    std_dev_values = close_prices.rolling(window=period).std()

    upper_band = middle_band + (std_dev * std_dev_values)
    lower_band = middle_band - (std_dev * std_dev_values)

    upper_result = []
    middle_result = []
    lower_result = []

    for i, date in enumerate(data['time']):
        if pd.notna(upper_band.iloc[i]):
            upper_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "upper_band": float(upper_band.iloc[i])
            })

        if pd.notna(middle_band.iloc[i]):
            middle_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "middle_band": float(middle_band.iloc[i])
            })

        if pd.notna(lower_band.iloc[i]):
            lower_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "lower_band": float(lower_band.iloc[i])
            })

    return {
        "upper_band": upper_result,
        "middle_band": middle_result,
        "lower_band": lower_result
    }


def calculate_stochastic_oscillator(data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    if len(data) < k_period:
        return {"error": "Insufficient data for Stochastic Oscillator calculation"}

    high_prices = data['high'].astype(float)
    low_prices = data['low'].astype(float)
    close_prices = data['close'].astype(float)

    lowest_low = low_prices.rolling(window=k_period).min()
    highest_high = high_prices.rolling(window=k_period).max()

    k_percent = 100 * ((close_prices - lowest_low) / (highest_high - lowest_low))

    d_percent = k_percent.rolling(window=d_period).mean()

    k_result = []
    d_result = []

    for i, date in enumerate(data['time']):
        if pd.notna(k_percent.iloc[i]):
            k_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "k_percent": float(k_percent.iloc[i])
            })

        if pd.notna(d_percent.iloc[i]):
            d_result.append({
                "date": date.strftime("%Y-%m-%d"),
                "d_percent": float(d_percent.iloc[i])
            })

    return {
        "k_percent": k_result,
        "d_percent": d_result
    }