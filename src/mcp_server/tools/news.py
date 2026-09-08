"""MCP tool: get_news_and_sentiment."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.portfolio.news_sentiment_service import handle_news_sentiment_query


@mcp.tool(
    name="get_news_and_sentiment",
    description="Fetch news/sentiment/social_volume for tickers. Cite [Nguồn: news - ticker].",
)
def get_news_and_sentiment(
    tickers: Annotated[list[str], Field(description="Tickers")],
    field: Annotated[str, Field(description="Field: news|sentiment|social_volume|all")] = "all",
    compare_with: Annotated[list[str] | None, Field(description="Reference tickers")] = None,
    days: Annotated[int | None, Field(description="Last N days")] = None,
    weeks: Annotated[int | None, Field(description="Last N weeks")] = None,
    months: Annotated[int | None, Field(description="Last N months")] = None,
) -> str:
    return call_service("get_news_and_sentiment", handle_news_sentiment_query, tickers=tickers, field=field, compare_with=compare_with, days=days, weeks=weeks, months=months)
