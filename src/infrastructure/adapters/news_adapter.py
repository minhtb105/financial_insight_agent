"""News adapter."""

from __future__ import annotations

from typing import Any

from vnstock import Company

from shared.ports.news_port import NewsPort


class NewsAdapter(NewsPort):
    def fetch_news(self, ticker: str) -> list[dict[str, Any]]:
        try:
            company = Company(symbol=ticker, source="VCI")
            df = company.news()
            if df is None or getattr(df, "empty", False):
                return []
            # Normalize DataFrame rows to dicts with expected keys
            out: list[dict[str, Any]] = []
            for _, row in df.iterrows():
                out.append({
                    "title": str(row.get("title", "")),
                    "content": str(row.get("content", row.get("title", ""))),
                    "source": str(row.get("source", "VCI")),
                    "url": str(row.get("url", "")),
                    "date": str(row.get("date", row.get("publish_date", ""))),
                    "ticker": ticker,
                })
            return out
        except Exception:
            return []
