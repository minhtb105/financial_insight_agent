from data.indicators import (
    get_aggregate_volume,
    get_price_stat,
)
from typing import Dict, Any


class AggregateService:
    """
    Handle aggregate_query:
    - Sum / average volume
    - min / max close price or open price
    """

    def handle(self, parsed: Dict[str, Any]):
        field = parsed.get("requested_field")

        try:
            if field == "volume" and parsed.get("aggregate") == "sum":
                return get_aggregate_volume(parsed)

            if field in ("open_price", "close_price") and parsed.get("aggregate"):
                return get_price_stat(parsed, parsed["aggregate"])

            return {"error": "Missing aggregate for this field"}

        except Exception as e:
            return {"error": str(e)}
