"""VNStock adapter implementing MarketDataPort."""

from __future__ import annotations

from typing import Any

from shared.ports.market_data_port import MarketDataPort
from infrastructure.api_clients.vn_stock_client import VNStockClient


class VNStockAdapter(MarketDataPort):
    def get_price_data(self, ticker: str, start_date: str, end_date: str, interval: str = "1d") -> dict[str, Any]:
        client = VNStockClient(ticker=ticker)
        data = client.fetch_trading_data(start=start_date, end=end_date, interval=interval)
        if data is None or getattr(data, "empty", False):
            return {"error": "No data available"}
        rows = []
        for _, row in data.iterrows():
            rows.append({
                "date": row["date"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            })
        return {"ticker": ticker, "data": rows, "start_date": start_date, "end_date": end_date}
