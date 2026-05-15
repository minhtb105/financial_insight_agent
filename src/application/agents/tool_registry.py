import json
import logging
from typing import Dict, Any, Optional

from langchain.tools import tool

logger = logging.getLogger(__name__)
TOOL_ERR_PREFIX = "TOOL_ERR#"

from application.services.financial.aggregate_service import handle_aggregate_query
from application.services.company.company_service import handle_company_query
from application.services.market.compare_service import handle_compare_query
from application.services.market.indicator_service import handle_indicator_query
from application.services.market.price_service import handle_price_query
from application.services.financial.ranking_service import handle_ranking_query
from application.services.financial.financial_ratio_service import handle_financial_ratio_query
from application.services.portfolio.news_sentiment_service import handle_news_sentiment_query
from application.services.portfolio.portfolio_service import handle_portfolio_query
from application.services.market.alert_service import handle_alert_query
from application.services.market.forecast_service import handle_forecast_query
from application.services.market.sector_service import handle_sector_query


# -------------------------
# Helpers
# -------------------------
def to_pretty_json(obj: Any) -> str:
    """Convert Python object to readable JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


# -------------------------
# Tools (wrapper for each handler)
# -------------------------

@tool("handle_price_query", description="""
Dùng KHI: query_type là "price_query". Lấy OHLCV, open, close, high, low, volume cho 1+ tickers.
Input: tickers (req), requested_field (open/close/high/low/volume/ohlcv), time.
KHÔNG dùng cho: chỉ báo kỹ thuật, xếp hạng, so sánh, tổng hợp, tỷ lệ tài chính.
""")
def handle_price_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing price_query payload."

    try:
        res = handle_price_query(query)
    except Exception as e:
        logger.exception("price_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling price_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for price_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_ranking_query", description="""
Dùng KHI: query_type là "ranking_query". Xếp hạng >=2 tickers theo field, aggregate=max/min/mean/latest.
Input: tickers (req,>=2), requested_field, aggregate, time.
KHÔNG dùng cho: so sánh 2 nhóm (dùng compare), tổng hợp số học (dùng aggregate).
""")
def handle_ranking_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing ranking_query payload."

    try:
        res = handle_ranking_query(query)
    except Exception as e:
        logger.exception("ranking_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling ranking_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for ranking_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_indicator_query", description="""
Dùng KHI: query_type là "indicator_query". Tính SMA/RSI/MACD cho 1+ tickers.
Input: tickers (req), requested_field (sma/rsi/macd), indicator_params, time.
KHÔNG dùng cho: giá OHLCV thô (dùng price_query), xếp hạng, so sánh.
""")
def handle_indicator_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing indicator_query payload."

    try:
        res = handle_indicator_query(query)
    except Exception as e:
        logger.exception("indicator_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling indicator_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for indicator_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_compare_query", description="""
Dùng KHI: query_type là "comparison_query". So sánh nhóm chính (tickers) vs tham chiếu (compare_with).
Input: tickers (req, nhóm chính), compare_with (req), requested_field, time.
KHÔNG dùng cho: 1 nhóm tickers (dùng price_query), tổng hợp (dùng aggregate).
""")
def handle_compare_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing compare_query payload."

    try:
        res = handle_compare_query(query)
    except Exception as e:
        logger.exception("compare_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling compare_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for compare_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_company_query", description="""
Dùng KHI: query_type là "company_query". Lấy cổ đông, ban lãnh đạo, công ty con.
Input: tickers (req), requested_field (shareholders/executives/subsidiaries).
KHÔNG dùng cho: giá cổ phiếu, chỉ báo kỹ thuật, tỷ lệ tài chính.
""")
def handle_company_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing company_query payload."

    try:
        res = handle_company_query(query)
    except Exception as e:
        logger.exception("company_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling company_query: {e}"

    if not res:
        return f"{TOOL_ERR_PREFIX} No data returned for company_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_aggregate_query", description="""
Dùng KHI: query_type là "aggregate_query". Tính mean/sum/median/std/min/max trên 1+ tickers.
Input: tickers (req), requested_field, aggregate_fn (mean/sum/median/std/min/max), time.
KHÔNG dùng cho: xếp hạng từng ticker (dùng ranking), so sánh (dùng compare).
""")
def handle_aggregate_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing aggregate_query payload."

    try:
        res = handle_aggregate_query(query)
    except Exception as e:
        logger.exception("aggregate_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling aggregate_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for aggregate_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_financial_ratio_query", description="""
Dùng KHI: query_type là "financial_ratio_query". Lấy PE, PB, ROE, EPS, debt_to_equity, v.v.
Input: tickers (req), requested_field, period/quarter/year (tùy chọn).
KHÔNG dùng cho: giá cổ phiếu, chỉ báo kỹ thuật, thông tin công ty.
""")
def handle_financial_ratio_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing financial_ratio_query payload."

    try:
        res = handle_financial_ratio_query(query)
    except Exception as e:
        logger.exception("financial_ratio_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling financial_ratio_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for financial_ratio_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_news_sentiment_query", description="""
Dùng KHI: query_type là "news_sentiment_query". Lấy tin tức, sentiment, social volume.
Input: tickers (req), requested_field (news/sentiment/social_volume), compare_with (tùy chọn), time.
KHÔNG dùng cho: giá cổ phiếu, chỉ báo kỹ thuật, tỷ lệ tài chính.
""")
def handle_news_sentiment_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing news_sentiment_query payload."

    try:
        res = handle_news_sentiment_query(query)
    except Exception as e:
        logger.exception("news_sentiment_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling news_sentiment_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for news_sentiment_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_portfolio_query", description="""
Dùng KHI: query_type là "portfolio_query". Quản lý danh mục: giá trị, hiệu suất, phân bổ ngành.
Input: requested_field, portfolio {ticker: sl} (tùy chọn), tickers (tùy chọn).
KHÔNG dùng cho: phân tích từng ticker, thông tin công ty, tin tức.
""")
def handle_portfolio_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing portfolio_query payload."

    try:
        res = handle_portfolio_query(query)
    except Exception as e:
        logger.exception("portfolio_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling portfolio_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for portfolio_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_alert_query", description="""
Dùng KHI: query_type là "alert_query". Cảnh báo giá khi ticker vượt ngưỡng.
Input: tickers (req), threshold (req), condition (above/below), timeframe.
KHÔNG dùng cho: dự báo, phân tích ngành, xếp hạng.
""")
def handle_alert_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing alert_query payload."

    try:
        res = handle_alert_query(query)
    except Exception as e:
        logger.exception("alert_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling alert_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for alert_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_forecast_query", description="""
Dùng KHI: query_type là "forecast_query". Dự báo giá cổ phiếu từ dữ liệu lịch sử.
Input: tickers (req), timeframe, model (tùy chọn).
KHÔNG dùng cho: chỉ báo kỹ thuật, cảnh báo giá, phân tích ngành.
""")
def handle_forecast_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing forecast_query payload."

    try:
        res = handle_forecast_query(query)
    except Exception as e:
        logger.exception("forecast_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling forecast_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for forecast_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


@tool("handle_sector_query", description="""
Dùng KHI: query_type là "sector_query". Phân tích hiệu suất cổ phiếu theo ngành.
Input: sector (req), metric (performance/volume), timeframe.
KHÔNG dùng cho: phân tích từng ticker, chỉ báo kỹ thuật.
""")
def handle_sector_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return f"{TOOL_ERR_PREFIX} Missing sector_query payload."

    try:
        res = handle_sector_query(query)
    except Exception as e:
        logger.exception("sector_query failed")
        return f"{TOOL_ERR_PREFIX} Error while handling sector_query: {e}"

    if res is None:
        return f"{TOOL_ERR_PREFIX} No data returned for sector_query."

    try:
        return to_pretty_json(res)
    except (TypeError, ValueError):
        return str(res)


# ---------------------------------------------------------------------------
# Tool Groups
# ---------------------------------------------------------------------------

TOOL_GROUPS: dict[str, dict] = {
    "market": {
        "label": "Thị trường",
        "tool_names": [
            "price_query", "indicator_query", "comparison_query",
            "ranking_query", "aggregate_query", "forecast_query",
        ],
    },
    "fundamental": {
        "label": "Cơ bản",
        "tool_names": ["financial_ratio_query", "company_query"],
    },
    "portfolio": {
        "label": "Danh mục & Tin tức",
        "tool_names": ["portfolio_query", "news_sentiment_query"],
    },
    "monitoring": {
        "label": "Cảnh báo & Ngành",
        "tool_names": ["alert_query", "sector_query"],
    },
}

_tool_by_query_type: dict[str, Any] = {
    "price_query": handle_price_query_tool,
    "indicator_query": handle_indicator_query_tool,
    "comparison_query": handle_compare_query_tool,
    "ranking_query": handle_ranking_query_tool,
    "aggregate_query": handle_aggregate_query_tool,
    "forecast_query": handle_forecast_query_tool,
    "financial_ratio_query": handle_financial_ratio_query_tool,
    "company_query": handle_company_query_tool,
    "portfolio_query": handle_portfolio_query_tool,
    "news_sentiment_query": handle_news_sentiment_query_tool,
    "alert_query": handle_alert_query_tool,
    "sector_query": handle_sector_query_tool,
}

TOOL_GROUP_MAP: dict[str, dict] = {}
group_tool_lists: dict[str, list] = {}
for gname, ginfo in TOOL_GROUPS.items():
    group_tools = {qt: _tool_by_query_type[qt] for qt in ginfo["tool_names"]}
    TOOL_GROUP_MAP[gname] = {"label": ginfo["label"], "tools": group_tools}
    group_tool_lists[gname] = list(group_tools.values())

TOOL_REGISTRY: dict[str, Any] = {}
for gm in TOOL_GROUP_MAP.values():
    TOOL_REGISTRY.update(gm["tools"])

QUERY_TYPE_TO_GROUP: dict[str, str] = {
    "price_query": "market",
    "indicator_query": "market",
    "comparison_query": "market",
    "ranking_query": "market",
    "aggregate_query": "market",
    "forecast_query": "market",
    "financial_ratio_query": "fundamental",
    "company_query": "fundamental",
    "portfolio_query": "portfolio",
    "news_sentiment_query": "portfolio",
    "alert_query": "monitoring",
    "sector_query": "monitoring",
}

ALL_TOOLS: list = list(_tool_by_query_type.values())

__all__ = [
    "TOOL_REGISTRY", "TOOL_GROUP_MAP", "group_tool_lists",
    "QUERY_TYPE_TO_GROUP", "to_pretty_json", "TOOL_ERR_PREFIX",
    "ALL_TOOLS",
]



