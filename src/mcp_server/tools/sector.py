"""MCP tool: analyze_sector."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.market.sector_service import handle_sector_query


@mcp.tool(
    name="analyze_sector",
    description="Analyze sector performance (banking|real_estate|technology|energy...). Cite [Nguồn: sector - name].",
)
def analyze_sector(
    sector: Annotated[str, Field(description="Sector name")],
    metric: Annotated[str, Field(description="performance|volume")] = "performance",
    timeframe: Annotated[str, Field(description="1w|1m...")] = "1w",
) -> str:
    return call_service("analyze_sector", handle_sector_query, sector=sector, metric=metric, timeframe=timeframe)
