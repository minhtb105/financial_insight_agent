"""MCP tool: get_company_info."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.company.company_service import handle_company_query


@mcp.tool(
    name="get_company_info",
    description="Fetch company info: shareholders|executives|subsidiaries. Cite [Nguồn: company - field - ticker].",
)
def get_company_info(
    tickers: Annotated[list[str], Field(description="Tickers")],
    field: Annotated[str, Field(description="Field: shareholders|executives|subsidiaries")] = "shareholders",
) -> str:
    return call_service("get_company_info", handle_company_query, tickers=tickers, field=field)
