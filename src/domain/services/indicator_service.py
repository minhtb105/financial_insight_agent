from data.indicators import get_sma, get_rsi
from typing import Dict, Any


class IndicatorService:
    """
    Handle indicator_query: SMA, RSI, MACD
    """

    def handle(self, parsed: Dict[str, Any]):
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
                return {"error": "Does not has any valid indicator"}

            return output

        except Exception as e:
            return {"error": str(e)}
