from data.indicators import (
    get_aggregate_volume,
    get_price_stat,
)
from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


class AggregateService:
    """
    Handle aggregate_query:
    - Sum / average volume
    - min / max close price or open price
    """
    def get_price_stat(self, query: dict, stat: str):
        client = VNStockClient(ticker=query["tickers"][0])
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval") or "1d",
        )
        if stat == "min":
            return df[query["requested_field"].replace("_price", "")].min()
        elif stat == "max":
            return df[query["requested_field"].replace("_price", "")].max()
        elif stat == "mean":
            return df[query["requested_field"].replace("_price", "")].mean()
        else:
            return None

    def get_aggregate_volume(self, query: dict):
        client = VNStockClient(ticker=query["tickers"][0])
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval") or "1d",
        )
    
        return df["volume"].sum()

    def handle(self, parsed: Dict[str, Any]):
        field = parsed.get("requested_field")

        try:
            if field == "volume" and parsed.get("aggregate") == "sum":
                return self.get_aggregate_volume(parsed)

            if field in ("open_price", "close_price") and parsed.get("aggregate"):
                return self.get_price_stat(parsed, parsed["aggregate"])

            return {"error": "Missing aggregate for this field"}

        except Exception as e:
            return {"error": str(e)}
