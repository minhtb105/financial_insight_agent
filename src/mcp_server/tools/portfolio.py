"""MCP tool: manage_portfolio."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.portfolio.portfolio_service import handle_portfolio_query


@mcp.tool(
    name="manage_portfolio",
    description="Manage portfolio: portfolio_value|portfolio_performance|portfolio_allocation|portfolio_summary. Cite [Nguồn: portfolio].",
)
def manage_portfolio(
    field: Annotated[str, Field(description="Field: portfolio_value|portfolio_performance|portfolio_allocation|portfolio_summary")] = "portfolio_summary",
    portfolio: Annotated[dict[str, int] | None, Field(description="Dict ticker->share_count")] = None,
) -> str:
    return call_service("manage_portfolio", handle_portfolio_query, field=field, portfolio=portfolio)
