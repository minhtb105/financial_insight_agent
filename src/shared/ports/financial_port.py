"""FinancialPort — abstract for financial statements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FinancialPort(ABC):
    @abstractmethod
    def get_financial_statement(self, ticker: str) -> Any:
        """Return financial statement DataFrame/dict."""

    @abstractmethod
    def get_market_data(self, ticker: str) -> Any:
        """Return market data dict."""
