"""MCP tool: compare_stocks — strict Literal for field."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.market.compare_service import handle_compare_query


@mcp.tool(
    name="compare_stocks",
    description="Compare price data between main tickers and reference compare_with. Strict field enum.",
)
def compare_stocks(
    tickers: Annotated[list[str], Field(description="Main tickers")],
    compare_with: Annotated[list[str], Field(description="Reference tickers")],
    field: Annotated[Literal["close", "open", "high", "low", "volume"], Field(description="Field")] = "close",
    days: Annotated[int | None, Field(description="Last N days")] = None,
    weeks: Annotated[int | None, Field(description="Last N weeks")] = None,
    months: Annotated[int | None, Field(description="Last N months")] = None,
    start_date: Annotated[str | None, Field(description="Start YYYY-MM-DD")] = None,
    end_date: Annotated[str | None, Field(description="End YYYY-MM-DD")] = None,
) -> str:
    return call_service("compare_stocks", handle_compare_query, tickers=tickers, compare_with=compare_with, field=field, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)
