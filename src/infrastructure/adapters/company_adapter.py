"""Company adapter."""

from __future__ import annotations

from typing import Any

from shared.ports.company_port import CompanyPort
from infrastructure.api_clients.vn_stock_client import VNStockClient


class CompanyAdapter(CompanyPort):
    def get_overview(self, ticker: str) -> Any:
        client = VNStockClient(ticker=ticker)
        return client.company.overview()

    def list_companies(self) -> Any:
        client = VNStockClient(ticker="VNINDEX")
        return client.company.overview()
