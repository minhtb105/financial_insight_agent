"""MCP tool: calculate_technical_indicator — strict Literal."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.market.indicator_service import handle_indicator_query


@mcp.tool(
    name="calculate_technical_indicator",
    description="Compute SMA/RSI/MACD for tickers. Cite as [TICKER: value, nguồn: calculate_technical_indicator]. Strict enums.",
)
def calculate_technical_indicator(
    tickers: Annotated[list[str], Field(description="Tickers, e.g. ['VCB']")],
    indicator: Annotated[Literal["sma", "rsi", "macd"], Field(description="Indicator")] = "sma",
    period: Annotated[int | None, Field(description="Lookback for SMA/RSI")] = None,
    fast_period: Annotated[int | None, Field(description="MACD fast (default 12)")] = None,
    slow_period: Annotated[int | None, Field(description="MACD slow (default 26)")] = None,
    days: Annotated[int | None, Field(description="Last N days")] = None,
    weeks: Annotated[int | None, Field(description="Last N weeks")] = None,
    months: Annotated[int | None, Field(description="Last N months")] = None,
    start_date: Annotated[str | None, Field(description="Start YYYY-MM-DD")] = None,
    end_date: Annotated[str | None, Field(description="End YYYY-MM-DD")] = None,
) -> str:
    return call_service("calculate_technical_indicator", handle_indicator_query, tickers=tickers, indicator=indicator, period=period, fast_period=fast_period, slow_period=slow_period, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)
