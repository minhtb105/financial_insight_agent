from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


"""
Handle comparison_query: Compare price / volume between tickers
"""
# ------------ Low-level handlers ----------------
def fetch_price_field(ticker: str, parsed: Dict[str, Any], col: str):
    """Fetch specific price field for ONE ticker"""
    client = VNStockClient(ticker=ticker)
    df, _ = client.fetch_trading_data(
        start=parsed.get("start"),
        end=parsed.get("end"),
        interval=parsed.get("interval") or "1d",
    )

    if df is None or df.empty:
        return None

    return df[["date", col]].to_dict(orient="records")


def fetch_volume_sum(ticker: str, parsed: Dict[str, Any]):
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
    General compare handler. Works for:
      - volume
      - open_price/close_price/high_price/low_price
      - ohlcv
    """

    tickers = parsed.get("tickers") or []
    compare_with = parsed.get("compare_with") or []
    field = parsed.get("requested_field")

    if not tickers and not compare_with:
        return {"error": "Missing ticker symbols"}

    # All symbols to compare
    symbols = tickers + compare_with if compare_with else tickers

    # === Mapping field → handler ===
    price_field_map = {
        "open_price": "open",
        "close_price": "close",
    }

    results = {}

    for symbol in symbols:
        if field == "volume":
            results[symbol] = fetch_volume_sum(symbol, parsed)

        elif field in price_field_map:
            col = price_field_map[field]
            results[symbol] = fetch_price_field(symbol, parsed, col)

        elif field == "ohlcv":
            results[symbol] = fetch_ohlcv(symbol, parsed)

        else:
            results[symbol] = {"error": f"Unsupported compare field: {field}"}

    return results
