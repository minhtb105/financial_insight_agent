from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


"""
Handle aggregate_query:
- Sum / average volume
- min / max close price or open price
"""


def get_price_stat(query: dict, stat: str):
    client = VNStockClient(ticker=query["tickers"][0])
    df = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )
    if stat == "min":
        return df[query["requested_field"]].min()
    elif stat == "max":
        return df[query["requested_field"]].max()
    elif stat == "mean":
        return df[query["requested_field"]].mean()
    else:
        return None


def get_aggregate_volume(query: dict, stat: str):
    client = VNStockClient(ticker=query["tickers"][0])
    df = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )

    if stat == "sum":
        return df["volume"].sum()
    elif stat == "mean":
        return df["volume"].mean()
    else:
        return None


def handle_aggregate_query(parsed: Dict[str, Any]):
    field = parsed.get("requested_field")

    try:
        aggregate = parsed.get("aggregate")
        if field == "volume" and aggregate in ["sum", "mean"]:
            return get_aggregate_volume(parsed, aggregate)

        if field in ("open", "close") and aggregate in ["min", "max", "mean"]:
            return get_price_stat(parsed, aggregate)

        return {"error": "Missing aggregate for this field"}

    except Exception as e:
        return {"error": str(e)}
