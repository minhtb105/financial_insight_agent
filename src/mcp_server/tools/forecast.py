"""MCP tool: forecast_stock_price."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.market.forecast_service import handle_forecast_query


@mcp.tool(
    name="forecast_stock_price",
    description="Forecast stock price via SMA+trend (timeframe 1d|1w|1m). ALWAYS add disclaimer giáo dục.",
)
def forecast_stock_price(
    tickers: Annotated[list[str], Field(description="Tickers")],
    timeframe: Annotated[str, Field(description="Horizon e.g. 1d|1w|1m")] = "1w",
) -> str:
    return call_service("forecast_stock_price", handle_forecast_query, tickers=tickers, timeframe=timeframe)
