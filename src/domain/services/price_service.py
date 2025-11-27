from data.indicators import (
    get_ohlcv, 
    get_price_field,
)
from typing import Dict, Any


class PriceService:
    """
    Handle price_query:
    - ohlcv
    - open_price, close_price
    - volume
    """

    def handle(self, parsed: Dict[str, Any]):
        field = parsed.get("requested_field")
        tickers = parsed.get("tickers") or []

        if not tickers:
            return {"error": "Missing ticker"}

        try:
            if field == "ohlcv":
                return get_ohlcv(parsed)

            if field in ("open_price", "close_price", "volume"):    
                return get_price_field(parsed)

            return {"error": f"requested_field is invalid for price_query: {field}"}

        except Exception as e:
            return {"error": str(e)}
