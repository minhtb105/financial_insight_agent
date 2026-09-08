"""MCP tool: get_financial_ratios."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.financial.financial_ratio_service import handle_financial_ratio_query


@mcp.tool(
    name="get_financial_ratios",
    description="Fetch financial ratios (pe/pb/roe/eps/current_ratio/debt_to_equity/profit_margin/quick_ratio/asset_turnover/dividend_yield). Cite [TICKER: value, nguồn: get_financial_ratios].",
)
def get_financial_ratios(
    tickers: Annotated[list[str], Field(description="Tickers")],
    field: Annotated[str, Field(description="Ratio field: pe|pb|roe|eps|current_ratio|debt_to_equity|profit_margin|quick_ratio|asset_turnover|dividend_yield")] = "pe",
) -> str:
    return call_service("get_financial_ratios", handle_financial_ratio_query, tickers=tickers, field=field)
