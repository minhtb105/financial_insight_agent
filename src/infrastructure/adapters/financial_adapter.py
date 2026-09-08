"""Financial adapter."""

from __future__ import annotations

from typing import Any

from shared.ports.financial_port import FinancialPort
from infrastructure.api_clients.vn_stock_client import VNStockClient


class FinancialAdapter(FinancialPort):
    def get_financial_statement(self, ticker: str) -> Any:
        client = VNStockClient(ticker=ticker)
        return client.company.financial_statement()

    def get_market_data(self, ticker: str) -> Any:
        client = VNStockClient(ticker=ticker)
        return client.company.market_data()
