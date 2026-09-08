"""MCP tool: check_price_alert."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.market.alert_service import handle_alert_query


@mcp.tool(
    name="check_price_alert",
    description="Set price alert when ticker crosses threshold (above|below). Cite [TICKER: threshold, nguồn: check_price_alert].",
)
def check_price_alert(
    tickers: Annotated[list[str], Field(description="Tickers")],
    threshold: Annotated[float, Field(description="Price threshold")],
    condition: Annotated[str, Field(description="above|below")] = "above",
    timeframe: Annotated[str, Field(description="Timeframe e.g. 1d")] = "1d",
) -> str:
    return call_service("check_price_alert", handle_alert_query, tickers=tickers, threshold=threshold, condition=condition, timeframe=timeframe)
