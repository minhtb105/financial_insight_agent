from data.indicators import (
    get_ohlcv, 
    get_price_field,
)
from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


class PriceService:
    """
    Handle price_query:
    - ohlcv
    - open_price, close_price
    - volume
    """

    def get_ohlcv(self, query: dict):
        client = VNStockClient(ticker=query["tickers"][0])
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval") or "1d",
        )
        
        return df.tail(5).to_dict(orient="records")

    def get_price_field(self, query: dict):
        """
        Return one of price field following requested_field:
        - close_price → close
        - open_price → open
        - high_price → high
        - low_price → low
        - volume → volume

        Output: DataFrame gồm 2 cột: date + value_field
        """

        client = VNStockClient(ticker=query["tickers"][0])
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval") or "1d",
        )

        if df is None or df.empty:
            return None

        mapping = {
            "close_price": "close",
            "open_price": "open",
            "high_price": "high",
            "low_price": "low",
            "volume": "volume",
        }

        requested = query.get("requested_field")

        if requested not in mapping:
            return None

        col = mapping[requested]

        if col not in df.columns:
            return None

        return df[["date", col]].to_dict(orient="records")

    def handle(self, parsed: Dict[str, Any]):
        field = parsed.get("requested_field")
        tickers = parsed.get("tickers") or []

        if not tickers:
            return {"error": "Missing ticker"}

        try:
            if field == "ohlcv":
                return self.get_ohlcv(parsed)

            if field in ("open_price", "close_price", "volume"):    
                return self.get_price_field(parsed)

            return {"error": f"requested_field is invalid for price_query: {field}"}

        except Exception as e:
            return {"error": str(e)}
