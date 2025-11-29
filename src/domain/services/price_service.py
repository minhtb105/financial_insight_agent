from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


"""
Handle price_query: ohlcv, open_price, close_price, volume
"""


def get_ohlcv(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    df = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )

    return df.tail(5).to_dict(orient="records")


def get_price_field(query: dict):
    """
    Return one of price field following requested_field: close, open, volume
    Output: date + value_field
    """

    client = VNStockClient(ticker=query["tickers"][0])
    df = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )

    if df is None or df.empty:
        return None

    requested = query.get("requested_field")

    return df[["date", requested]].to_dict(orient="records")


def handle_price_query(parsed: Dict[str, Any]):
    field = parsed.get("requested_field")
    try:
        if field == "ohlcv":
            return get_ohlcv(parsed)

        if field in ("open", "close", "volume"):
            return get_price_field(parsed)

        return {"error": f"requested_field is invalid for price_query: {field}"}

    except Exception as e:
        return {"error": str(e)}
