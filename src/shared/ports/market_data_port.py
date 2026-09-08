"""MarketDataPort — abstraction for price/trading data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketDataPort(ABC):
    @abstractmethod
    def get_price_data(self, ticker: str, start_date: str, end_date: str, interval: str = "1d") -> dict[str, Any]:
        """Return dict {ticker, data:[{date,open,high,low,close,volume}], start_date, end_date} or {error}."""
