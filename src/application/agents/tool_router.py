from typing import Any, Dict

from application.agents.tool_registry import (
    handle_company_query_tool,
    handle_price_query_tool,
    handle_aggregate_query_tool,
    handle_compare_query_tool,
    handle_indicator_query_tool,
    handle_ranking_query_tool,
    handle_financial_ratio_query_tool,
    handle_news_sentiment_query_tool,
    handle_portfolio_query_tool,
    handle_alert_query_tool,
    handle_forecast_query_tool,
    handle_sector_query_tool,
)
from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var

logger = get_logger(__name__)

TOOL_ROUTER: Dict[str, Any] = {
    "price_query": handle_price_query_tool,
    "company_query": handle_company_query_tool,
    "financial_ratio_query": handle_financial_ratio_query_tool,
    "comparison_query": handle_compare_query_tool,
    "aggregate_query": handle_aggregate_query_tool,
    "indicator_query": handle_indicator_query_tool,
    "ranking_query": handle_ranking_query_tool,
    "news_sentiment_query": handle_news_sentiment_query_tool,
    "portfolio_query": handle_portfolio_query_tool,
    "alert_query": handle_alert_query_tool,
    "forecast_query": handle_forecast_query_tool,
    "sector_query": handle_sector_query_tool,
}


def route_to_tool(parsed_query: Dict[str, Any]) -> str:
    query_type = parsed_query.get("query_type", "")
    tool_fn = TOOL_ROUTER.get(query_type)
    rid = request_id_var.get() or "unknown"

    if tool_fn is None:
        logger.warning("Unknown query_type, falling back to price_query", extra={
            "request_id": rid,
            "query_type": query_type,
            "fallback": "price_query",
        })
        tool_fn = handle_price_query_tool
    else:
        logger.info("Routing to tool", extra={
            "request_id": rid,
            "query_type": query_type,
            "tool": tool_fn.__name__ if hasattr(tool_fn, '__name__') else type(tool_fn).__name__,
        })

    result = tool_fn.invoke(input={"query": parsed_query})

    logger.info("Tool execution completed", extra={
        "request_id": rid,
        "query_type": query_type,
        "result_length": len(result) if isinstance(result, str) else 0,
    })

    return result