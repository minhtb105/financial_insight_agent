from data.indicators import (
    get_min_open_across_tickers,
    get_price_stat,
    get_price_field,
)
from typing import Dict, Any


class RankingService:
    """
    Handle ranking_query:
    """

    def handle(self, parsed: Dict[str, Any]):
        try:
            # Special case: min open price
            if parsed.get("requested_field") == "open_price" and parsed.get("aggregate") == "min":
                return get_min_open_across_tickers(parsed)

            results = {}
            for t in parsed.get("tickers", []):
                q = dict(parsed)
                q["tickers"] = [t]

                if parsed.get("aggregate"):
                    results[t] = get_price_stat(q, parsed["aggregate"])
                else:
                    values = get_price_field(q)
                    results[t] = values[-1] if values else None

            # choose winner
            if parsed.get("aggregate") in ("min", "max"):
                key_fn = min if parsed["aggregate"] == "min" else max
                winner = key_fn(results.items(), key=lambda x: x[1])[0]
                
                return {"winner": winner, "details": results}

            return results

        except Exception as e:
            return {"error": str(e)}
