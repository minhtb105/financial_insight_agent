"""NewsPort — abstract for news fetching."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class NewsPort(ABC):
    @abstractmethod
    def fetch_news(self, ticker: str) -> list[dict[str, Any]]:
        """Return list of articles normalized {title,content,source,url,date,ticker}."""
