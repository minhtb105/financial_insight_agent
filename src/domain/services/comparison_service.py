from data.indicators import (
    get_price_field,
    get_ohlcv,
    compare_volume,
)
from typing import Dict, Any


class ComparisonService:
    """
    Handle comparison_query:
    - Cpmare price / volume between tickers
    """

    def handle(self, parsed: Dict[str, Any]):
        tickers = parsed.get("tickers") or []
        compare_with = parsed.get("compare_with") or []

        if not tickers and not compare_with:
            return {"error": "Missing ticker"}

        field = parsed.get("requested_field")

        try:
            # Special case: volume
            if field == "volume":
                return compare_volume(parsed)

            # Compare price field
            results = {}
            all_tickers = [tickers[0]] + compare_with if tickers else compare_with

            for sym in all_tickers:
                q = dict(parsed)
                q["tickers"] = [sym]

                if field in ("open_price", "close_price", "high_price", "low_price"):
                    results[sym] = get_price_field(q)
                else:
                    results[sym] = get_ohlcv(q)

            return results

        except Exception as e:
            return {"error": str(e)}
