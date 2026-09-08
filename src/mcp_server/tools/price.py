"""MCP tool: get_stock_price — strict Literal for field."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.market.price_service import handle_price_query


@mcp.tool(
    name="get_stock_price",
    description="Fetch OHLCV price data for one or more tickers. ALWAYS cite as [TICKER: value, nguồn: get_stock_price]. Do NOT use for indicators/ranking/comparison/aggregation. Field enum is strict.",
)
def get_stock_price(
    tickers: Annotated[list[str], Field(description="List of Vietnamese tickers, e.g. ['VCB','FPT']")],
    field: Annotated[Literal["close", "open", "high", "low", "volume", "ohlcv"], Field(description="Price field")] = "close",
    days: Annotated[int | None, Field(description="Last N days")] = None,
    weeks: Annotated[int | None, Field(description="Last N weeks")] = None,
    months: Annotated[int | None, Field(description="Last N months")] = None,
    start_date: Annotated[str | None, Field(description="Start YYYY-MM-DD")] = None,
    end_date: Annotated[str | None, Field(description="End YYYY-MM-DD")] = None,
) -> str:
    return call_service("get_stock_price", handle_price_query, tickers=tickers, field=field, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)
