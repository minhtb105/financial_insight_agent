from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


class ComparisonService:
    """
    Handle comparison_query:
    - Cpmare price / volume between tickers
    """
    def compare_volume(self, query: dict):
        results = {}
        for ticker in [query["tickers"][0]] + (query.get("compare_with") or []):
            client = VNStockClient(ticker=ticker)
            df, _ = client.fetch_trading_data(
                start=query.get("start"),
                end=query.get("end"),
                interval=query.get("interval") or "1d",
            )
            results[ticker] = df["volume"].sum()
            
        return results

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
        tickers = parsed.get("tickers") or []
        compare_with = parsed.get("compare_with") or []

        if not tickers and not compare_with:
            return {"error": "Missing ticker"}

        field = parsed.get("requested_field")

        try:
            # Special case: volume
            if field == "volume":
                return self.compare_volume(parsed)

            # Compare price field
            results = {}
            all_tickers = [tickers[0]] + compare_with if tickers else compare_with

            for sym in all_tickers:
                q = dict(parsed)
                q["tickers"] = [sym]

                if field in ("open_price", "close_price", "high_price", "low_price"):
                    results[sym] = self.get_price_field(q)
                else:
                    results[sym] = self.get_ohlcv(q)

            return results

        except Exception as e:
            return {"error": str(e)}
