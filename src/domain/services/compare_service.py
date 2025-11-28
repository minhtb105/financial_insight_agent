from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


"""
Handle comparison_query: Compare price / volume between tickers
"""

# ------------ Low-level handlers ----------------


def fetch_price_field(ticker: str, parsed: Dict[str, Any], col: str):
    """Fetch single price field (open/close/high/low) for ONE ticker."""
    client = VNStockClient(ticker=ticker)
    df, _ = client.fetch_trading_data(
        start=parsed.get("start"),
        end=parsed.get("end"),
        interval=parsed.get("interval") or "1d",
    )

    if df is None or df.empty:
        return None

    if col not in df.columns:
        return None

    return df[["date", col]].to_dict(orient="records")


def fetch_volume_sum(ticker: str, parsed: Dict[str, Any]):
    """Total traded volume."""
    client = VNStockClient(ticker=ticker)
    df, _ = client.fetch_trading_data(
        start=parsed.get("start"),
        end=parsed.get("end"),
        interval=parsed.get("interval") or "1d",
    )

    if df is None or df.empty:
        return None

    return int(df["volume"].sum())


def fetch_ohlcv(ticker: str, parsed: Dict[str, Any]):
    """Return last 5 rows of OHLCV."""
    client = VNStockClient(ticker=ticker)
    df, _ = client.fetch_trading_data(
        start=parsed.get("start"),
        end=parsed.get("end"),
        interval=parsed.get("interval") or "1d",
    )

    if df is None or df.empty:
        return None

    return df.tail(5).to_dict(orient="records")


# ------------ Unified compare engine ----------------

def compare_fields(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    General compare handler for fields:
      - open, close, high, low
      - volume
      - ohlcv
    """

    field = parsed.get("requested_field")
    tickers = parsed.get("tickers") or []
    compare_with = parsed.get("compare_with") or []

    if not tickers and not compare_with:
        return {"error": "Missing ticker symbols"}

    symbols = tickers + compare_with if compare_with else tickers
    results = {}

    for symbol in symbols:

        if field == "volume":
            results[symbol] = fetch_volume_sum(symbol, parsed)

        elif field in ("open", "close"):
            results[symbol] = fetch_price_field(symbol, parsed, field)

        elif field == "ohlcv":
            results[symbol] = fetch_ohlcv(symbol, parsed)

        else:
            results[symbol] = {"error": f"Unsupported compare field: {field}"}

    return results
