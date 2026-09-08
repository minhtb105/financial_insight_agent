"""CompanyPort — abstract for company overview / listing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CompanyPort(ABC):
    @abstractmethod
    def get_overview(self, ticker: str) -> Any:
        """Return DataFrame or dict for company overview."""

    @abstractmethod
    def list_companies(self) -> Any:
        """Return list/DataFrame of companies for sector discovery (VNINDEX)."""
