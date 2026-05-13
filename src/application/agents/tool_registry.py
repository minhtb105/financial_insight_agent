import json
from typing import Dict, Any, Optional

from langchain.tools import tool

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
Dùng KHI: query_type là "price_query". Lấy giá OHLCV, open, close, high, low, volume theo ngày cho 1+ tickers.

Input schema:
  query.tickers: list[str]              # bắt buộc, >= 1
  query.requested_field: one of [open, close, high, low, volume, ohlcv]  # mặc định "close"
  query.start / query.end: "YYYY-MM-DD" # hoặc days/weeks/months

KHÔNG dùng cho: chỉ báo kỹ thuật (SMA/RSI/MACD), xếp hạng, so sánh, tổng hợp, tỷ lệ tài chính, tin tức, thông tin công ty, danh mục.
""")
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


@tool("handle_ranking_query", description="""
Dùng KHI: query_type là "ranking_query". Xếp hạng >= 2 tickers theo một field. Trả về danh sách xếp hạng từ cao đến thấp (hoặc thấp đến cao nếu aggregate=min).

Input schema:
  query.tickers: list[str]              # bắt buộc, >= 2 phần tử
  query.requested_field: one of [open, close, volume]  # mặc định "close"
  query.aggregate: one of [max, min, mean, latest]     # mặc định "max"
  query.start / query.end               # thời gian

KHÔNG dùng cho: 1 ticker, so sánh 2 nhóm (dùng compare), tổng hợp số học gộp data points (dùng aggregate).
""")
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


@tool("handle_indicator_query", description="""
Dùng KHI: query_type là "indicator_query". Tính chỉ báo kỹ thuật SMA, RSI, MACD cho 1+ tickers.

Input schema:
  query.tickers: list[str]              # bắt buộc
  query.requested_field: one of [sma, rsi, macd]         # mặc định "sma"
  query.indicator_params: dict          # {sma: [periods], rsi: [periods], macd: [(fast, slow)]}
  query.start / query.end               # thời gian

KHÔNG dùng cho: giá OHLCV thô (dùng price_query), xếp hạng, so sánh, tỷ lệ tài chính, thông tin công ty.
""")
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


@tool("handle_compare_query", description="""
Dùng KHI: query_type là "comparison_query". So sánh 2 nhóm tickers: nhóm chính (tickers) vs nhóm tham chiếu (compare_with). Trả về thống kê và % chênh lệch.

Input schema:
  query.tickers: list[str]              # bắt buộc, nhóm chính
  query.compare_with: list[str]         # bắt buộc, nhóm tham chiếu
  query.requested_field: one of [open, close, volume]  # mặc định "close"
  query.start / query.end               # thời gian

KHÔNG dùng cho: xếp hạng đơn thuần (dùng ranking), 1 nhóm tickers, tổng hợp số học (dùng aggregate).
""")
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


@tool("handle_company_query", description="""
Dùng KHI: query_type là "company_query". Lấy thông tin công ty: cổ đông, ban lãnh đạo, công ty con.

Input schema:
  query.tickers: list[str]              # bắt buộc
  query.requested_field: one of [shareholders, executives, subsidiaries]  # mặc định "shareholders"

KHÔNG dùng cho: giá cổ phiếu, chỉ báo kỹ thuật, tỷ lệ tài chính (dùng financial_ratio), tin tức, danh mục.
""")
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


@tool("handle_aggregate_query", description="""
Dùng KHI: query_type là "aggregate_query". Tính tổng hợp số học trên >= 2 tickers. Gộp tất cả data points, tính mean/sum/median/std/min/max.

Input schema:
  query.tickers: list[str]              # bắt buộc, >= 2 phần tử
  query.requested_field: one of [open, close, volume]  # mặc định "close"
  query.aggregate: one of [mean, sum, median, std, min, max]  # mặc định "mean"
  query.start / query.end               # thời gian

KHÔNG dùng cho: 1 ticker, xếp hạng từng ticker riêng lẻ (dùng ranking), so sánh 2 nhóm (dùng compare).
""")
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


@tool("handle_financial_ratio_query", description="""
Dùng KHI: query_type là "financial_ratio_query". Lấy tỷ lệ tài chính doanh nghiệp: PE, PB, ROE, EPS, debt_to_equity, current_ratio, profit_margin, dividend_yield, v.v.

Input schema:
  query.tickers: list[str]              # bắt buộc
  query.requested_field: one of [pe, pb, roe, eps, debt_to_equity, current_ratio, profit_margin, quick_ratio, asset_turnover, dividend_yield]  # mặc định "pe"
  query.period / query.quarter / query.year  # tùy chọn

KHÔNG dùng cho: giá cổ phiếu, chỉ báo kỹ thuật, thông tin công ty (cổ đông/lãnh đạo), tin tức.
""")
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


@tool("handle_news_sentiment_query", description="""
Dùng KHI: query_type là "news_sentiment_query". Lấy tin tức, điểm sentiment, social volume cho 1+ tickers.

Input schema:
  query.tickers: list[str]              # bắt buộc
  query.requested_field: one of [news, sentiment, social_volume]  # mặc định "news"
  query.compare_with: list[str]         # tùy chọn, chỉ dùng cho so sánh sentiment
  query.days / query.weeks / query.months   # thời gian

KHÔNG dùng cho: giá cổ phiếu, chỉ báo kỹ thuật, tỷ lệ tài chính, thông tin công ty, xếp hạng.
""")
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


@tool("handle_portfolio_query", description="""
Dùng KHI: query_type là "portfolio_query". Quản lý danh mục đầu tư: giá trị, hiệu suất, phân bổ ngành.

Input schema:
  query.requested_field: one of [portfolio_value, portfolio_performance, portfolio_allocation]  # mặc định trả về tất cả
  query.portfolio: dict[str, int]      # tùy chọn {ticker: so_luong}
  query.tickers: list[str]             # tùy chọn

KHÔNG dùng cho: phân tích từng ticker riêng lẻ, thông tin công ty, tin tức, tỷ lệ tài chính.
""")
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


@tool("handle_alert_query", description="""
Dùng KHI: query_type là "alert_query". Thiết lập cảnh báo giá khi ticker vượt ngưỡng.

Input schema:
  query.tickers: list[str]              # bắt buộc
  query.threshold: float                # bắt buộc, mức giá ngưỡng
  query.condition: one of [above, below]  # mặc định "above"
  query.timeframe: str                  # mặc định "1d"

KHÔNG dùng cho: giá OHLCV thô, dự báo, phân tích ngành, xếp hạng.
""")
def handle_alert_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing alert_query payload."

    try:
        res = handle_alert_query(query)
    except Exception as e:
        return f"Error while handling alert_query: {e}"

    if res is None:
        return "No data returned for alert_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_forecast_query", description="""
Dùng KHI: query_type là "forecast_query". Dự báo giá cổ phiếu dựa trên dữ liệu lịch sử.

Input schema:
  query.tickers: list[str]              # bắt buộc
  query.timeframe: str                  # mặc định "1w"
  query.model: str                      # tùy chọn

KHÔNG dùng cho: giá hiện tại, chỉ báo kỹ thuật, cảnh báo giá, phân tích ngành.
""")
def handle_forecast_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing forecast_query payload."

    try:
        res = handle_forecast_query(query)
    except Exception as e:
        return f"Error while handling forecast_query: {e}"

    if res is None:
        return "No data returned for forecast_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


@tool("handle_sector_query", description="""
Dùng KHI: query_type là "sector_query". Phân tích hiệu suất cổ phiếu theo ngành.

Input schema:
  query.sector: str                     # bắt buộc, tên ngành
  query.metric: one of [performance, volume]  # mặc định "performance"
  query.timeframe: str                  # mặc định "1w"

KHÔNG dùng cho: phân tích từng ticker riêng lẻ, chỉ báo kỹ thuật, tỷ lệ tài chính.
""")
def handle_sector_query_tool(query: Optional[Dict[str, Any]] = None) -> str:
    if query is None:
        return "Missing sector_query payload."

    try:
        res = handle_sector_query(query)
    except Exception as e:
        return f"Error while handling sector_query: {e}"

    if res is None:
        return "No data returned for sector_query."

    try:
        return to_pretty_json(res)
    except Exception:
        return str(res)


TOOL_REGISTRY: Dict[str, Any] = {
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


if __name__ == "__main__":
    from infrastructure.llm.nlp_parser import QueryParser
    from application.services.market.indicator_service import handle_indicator_query
    parser = QueryParser()

    # q1 = "Giá đóng cửa của FPT tuần trước là bao nhiêu?"
    # parsed = parser.parse(q1)
    # print(q1)
    # print(parsed)
    # print(handle_price_query_tool.run(parsed))
    # print("\n")

    # q2 = "Trong các mã FPT, MWG và VNM, mã nào có giá đóng cửa cao nhất trong 2 tháng vừa qua?"
    # parsed = parser.parse(q2)
    # print(q2)
    # print(parsed)
    # print(handle_ranking_query(parsed))
    # print(handle_ranking_query_tool.run(parsed))
    # print("\n")

    q3 = "Tính cho tôi SMA9 của mã VIC trong 2 tuần với timeframe 1d"
    parsed = parser.parse(q3)
    print(q3)
    print(parsed)
    print(handle_indicator_query(parsed))
    print("\n")

    # q4 = "So sánh khối lượng giao dịch của FPT với MWG trong 7 ngày qua."
    # parsed = parser.parse(q4)
    # print(q4)
    # print(parsed)
    # print(handle_compare_query_tool.run(parsed))
    # print("\n")

    # q5 = "Những cổ đông lớn nhất của VNM là ai?"
    # parsed = parser.parse(q5)
    # print(q5)
    # print(parsed)
    # print(handle_company_query_tool.run(parsed))
    # print("\n")

    # q6 = "Tổng khối lượng giao dịch của FPT từ tháng 1 đến tháng 3 là bao nhiêu?"
    # parsed = parser.parse(q6)
    # print(q6)
    # print(parsed)
    # print(handle_aggregate_query_tool.run(parsed))
    # print("\n")
