import json
from typing import Dict, Any, Optional

from langchain.tools import tool

from domain.services.financial.aggregate_service import handle_aggregate_query
from domain.services.company.company_service import handle_company_query
from domain.services.market.compare_service import handle_compare_query
from domain.services.market.indicator_service import handle_indicator_query
from domain.services.market.price_service import handle_price_query
from domain.services.financial.ranking_service import handle_ranking_query
from domain.services.financial.financial_ratio_service import handle_financial_ratio_query
from domain.services.portfolio.news_sentiment_service import handle_news_sentiment_query
from domain.services.portfolio.portfolio_service import handle_portfolio_query


# -------------------------
# Helpers
# -------------------------
def to_pretty_json(obj: Any) -> str:
    """Convert Python object to readable JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


# -------------------------
# Enhanced Tools (wrapper for each handler)
# -------------------------

@tool("handle_price_query", description="Handle price_query (open/close/volume/ohlcv).")
def handle_price_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing price_query payload."

    try:
        res = handle_price_query(query)
    except Exception as e:
        return f"Error while handling price_query: {e}"

    if res is None:
        return "No data returned for price_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_ranking_query", description="Handle ranking_query (min/max/mean across multiple tickers).")
def handle_ranking_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing ranking_query payload."

    try:
        res = handle_ranking_query(query)
    except Exception as e:
        return f"Error while handling ranking_query: {e}"

    if res is None:
        return "No data returned for ranking_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_indicator_query", description="Handle indicator_query (SMA/RSI/MACD).")
def handle_indicator_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing indicator_query payload."

    try:
        res = handle_indicator_query(query)
    except Exception as e:
        return f"Error while handling indicator_query: {e}"

    if res is None:
        return "No data returned for indicator_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_compare_query", description="Handle compare_query — compare tickers vs compare_with.")
def handle_compare_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing compare_query payload."

    try:
        res = handle_compare_query(query)
    except Exception as e:
        return f"Error while handling compare_query: {e}"

    if res is None:
        return "No data returned for compare_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_company_query", description="Handle company_query (shareholders/executives/subsidiaries).")
def handle_company_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing company_query payload."

    try:
        res = handle_company_query(query)
    except Exception as e:
        return f"Error while handling company_query: {e}"

    if not res:
        return "No data returned for company_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_aggregate_query", description="Handle aggregate_query (sum/min/max/mean over fields).")
def handle_aggregate_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing aggregate_query payload."

    try:
        res = handle_aggregate_query(query)
    except Exception as e:
        return f"Error while handling aggregate_query: {e}"

    if res is None:
        return "No data returned for aggregate_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_financial_ratio_query", description="Handle financial_ratio_query (P/E, ROE, EPS, etc.).")
def handle_financial_ratio_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing financial_ratio_query payload."

    try:
        res = handle_financial_ratio_query(query)
    except Exception as e:
        return f"Error while handling financial_ratio_query: {e}"

    if res is None:
        return "No data returned for financial_ratio_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_news_sentiment_query", description="Handle news_sentiment_query (news, sentiment, social_volume).")
def handle_news_sentiment_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing news_sentiment_query payload."

    try:
        res = handle_news_sentiment_query(query)
    except Exception as e:
        return f"Error while handling news_sentiment_query: {e}"

    if res is None:
        return "No data returned for news_sentiment_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_portfolio_query", description="Handle portfolio_query (portfolio_value, performance, allocation).")
def handle_portfolio_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing portfolio_query payload."

    try:
        res = handle_portfolio_query(query)
    except Exception as e:
        return f"Error while handling portfolio_query: {e}"

    if res is None:
        return "No data returned for portfolio_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


# -------------------------
# Tool Registry
# -------------------------
ENHANCED_TOOLS = [
    handle_price_query_tool,
    handle_ranking_query_tool,
    handle_indicator_query_tool,
    handle_compare_query_tool,
    handle_company_query_tool,
    handle_aggregate_query_tool,
    handle_financial_ratio_query_tool,
    handle_news_sentiment_query_tool,
    handle_portfolio_query_tool,
]


