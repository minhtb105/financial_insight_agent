from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


def get_price_series(query: dict):
    """
    Fetch OHLCV data for a single ticker and extract the target price field.

    Returns:
        pandas.Series or None
    """
    ticker = query["tickers"][0]
    field = query.get("requested_field")

    df = VNStockClient(ticker=ticker).fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )

    if df is None or df.empty:
        return None

    return df[field]


def get_price_stat(query: dict):
    """
    Compute an aggregate statistic (min / max / mean)
    for a single ticker.
    """
    series = get_price_series(query)
    if series is None:
        return None

    agg = query.get("aggregate")

    if agg == "min":
        return float(series.min())
    elif agg == "max":
        return float(series.max())
    elif agg == "mean":
        return float(series.mean())

    return None


def handle_ranking_query(parsed: Dict[str, Any]):
    """
    Handle multi-ticker price aggregation:
    - min close price across tickers
    - max open price across tickers
    - average volume across tickers
    """

    requested_field = parsed.get("requested_field")
    aggregate = parsed.get("aggregate")
    tickers = parsed.get("tickers", [])

    if requested_field not in ("open", "close", "volume"):
        return {"error": "Invalid requested_field for price aggregation"}

    if aggregate not in ("min", "max", "mean"):
        return {"error": "Invalid aggregate (must be min/max/mean)"}

    results = {}

    for t in tickers:
        q = dict(parsed)
        q["tickers"] = [t]
        value = get_price_stat(q)
        results[t] = value

    # If comparing across tickers (min/max)
    if aggregate in ("min", "max"):
        winner = (
            min(results.items(), key=lambda x: x[1])[0]
            if aggregate == "min"
            else max(results.items(), key=lambda x: x[1])[0]
        )

        return {
            "winner": winner,
            "value": results[winner],
            "details": results,
        }

    return results
