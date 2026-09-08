"""MCP tool: aggregate_prices — strict Literal for field & aggregate_fn."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.financial.aggregate_service import handle_aggregate_query


@mcp.tool(
    name="aggregate_prices",
    description="Compute statistical aggregation (mean/sum/median/std/min/max) over tickers. Strict enums. Cite as [TICKER: value, nguồn: aggregate_prices].",
)
def aggregate_prices(
    tickers: Annotated[list[str], Field(description="Tickers")],
    field: Annotated[Literal["close", "open", "high", "low", "volume"], Field(description="Field")] = "close",
    aggregate_fn: Annotated[Literal["mean", "sum", "median", "std", "min", "max"], Field(description="Aggregation fn")] = "mean",
    days: Annotated[int | None, Field(description="Last N days")] = None,
    weeks: Annotated[int | None, Field(description="Last N weeks")] = None,
    months: Annotated[int | None, Field(description="Last N months")] = None,
    start_date: Annotated[str | None, Field(description="Start YYYY-MM-DD")] = None,
    end_date: Annotated[str | None, Field(description="End YYYY-MM-DD")] = None,
) -> str:
    return call_service("aggregate_prices", handle_aggregate_query, tickers=tickers, field=field, aggregate_fn=aggregate_fn, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)
