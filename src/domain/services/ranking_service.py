from data.indicators import (
    get_min_open_across_tickers,
    get_price_stat,
    get_price_field,
)
from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


class RankingService:
    """
    Handle ranking_query:
    """
    def get_min_open_across_tickers(self, query: dict):
        """
        Find the smallest open price over N days ago.
        
        tickers = ["BID", "TCB", "VCB"]
        requested_field = "open_price"
        aggregate = "min"
        """

        tickers = query["tickers"]
        start = query.get("start")
        end = query.get("end")
        interval = query.get("interval") or "1d"

        results = {}

        for ticker in tickers:
            client = VNStockClient(ticker=ticker)
            df, _ = client.fetch_trading_data(start=start, end=end, interval=interval)

            if df is None or df.empty:
                continue

            min_open = df["open"].min()
            results[ticker] = min_open

        if not results:
            return None

        lowest_ticker = min(results, key=results.get)

        return {
            "ticker": lowest_ticker,
            "min_open": results[lowest_ticker],
            "details": results
        }

    def handle(self, parsed: Dict[str, Any]):
        try:
            # Special case: min open price
            if parsed.get("requested_field") == "open_price" and parsed.get("aggregate") == "min":
                return self.get_min_open_across_tickers(parsed)

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
