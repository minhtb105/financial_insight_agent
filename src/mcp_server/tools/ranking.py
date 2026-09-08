"""MCP tool: rank_stocks — strict Literal for field & aggregate."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.financial.ranking_service import handle_ranking_query


@mcp.tool(
    name="rank_stocks",
    description="Rank 2+ tickers by a price field. Requires at least 2 tickers. Strict enums.",
)
def rank_stocks(
    tickers: Annotated[list[str], Field(description="Tickers to rank (≥2)")],
    field: Annotated[Literal["close", "open", "high", "low", "volume"], Field(description="Field")] = "close",
    aggregate: Annotated[Literal["max", "min", "mean", "latest"], Field(description="Aggregation")] = "max",
    days: Annotated[int | None, Field(description="Last N days")] = None,
    weeks: Annotated[int | None, Field(description="Last N weeks")] = None,
    months: Annotated[int | None, Field(description="Last N months")] = None,
    start_date: Annotated[str | None, Field(description="Start YYYY-MM-DD")] = None,
    end_date: Annotated[str | None, Field(description="End YYYY-MM-DD")] = None,
) -> str:
    return call_service("rank_stocks", handle_ranking_query, tickers=tickers, field=field, aggregate=aggregate, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)
