from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient
import pandas as pd


def calculate_sma(df: pd.DataFrame, window: int):
    return df["close"].rolling(window=window).mean()

def calculate_rsi(df: pd.DataFrame, window: int = 14):
    # Price change
    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

"""
Handle indicator_query: SMA, RSI, MACD
"""
def get_sma(query: dict):
    window_sizes = query.get("indicator_params", {}).get("sma", [9])
    if not isinstance(window_sizes, (list, tuple)):
        window_sizes = [int(window_sizes)]

    client = VNStockClient(ticker=query["tickers"][0])
    df = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
        window_size=max(window_sizes),
    )

    result = {}
    for w in window_sizes:
        df[f"SMA{w}"] = calculate_sma(df, w)
        result[f"SMA{w}"] = float(df[f"SMA{w}"].iloc[-1])

    return result


def get_rsi(query: dict):
    window_sizes = query.get("indicator_params", {}).get("rsi", [14])
    if not isinstance(window_sizes, (list, tuple)):
        window_sizes = [int(window_sizes)]

    client = VNStockClient(ticker=query["tickers"][0])
    df = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
        window_size=max(window_sizes),
    )

    result = {}
    for w in window_sizes:
        df[f"RSI{w}"] = calculate_rsi(df, w)
        result[f"RSI{w}"] = float(df[f"RSI{w}"].iloc[-1])

    return result


def handle(parsed: Dict[str, Any]):
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    params = parsed.get("indicator_params") or {}
    output = {}

    try:
        if "sma" in params:
            output["sma"] = get_sma(parsed)

        if "rsi" in params:
            output["rsi"] = get_rsi(parsed)

        if not output:
            return {"error": "Does not have any valid indicator"}

        return output

    except Exception as e:
        return {"error": str(e)}
    