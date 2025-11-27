import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from langchain.tools import tool

from data.indicators import (
    get_company_info,
    get_ohlcv,
    get_min_open_across_tickers,
    get_price_field,
    get_price_stat,
    get_aggregate_volume,
    compare_volume,
    get_sma,
    get_rsi,
)


# -------------------------
# Helpers
# -------------------------
def to_pretty_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _ensure_list(x):
    if x is None:
        return []
    
    if isinstance(x, list):
        return x
    
    # if comma separated string
    if isinstance(x, str):
        return [t.strip().upper() for t in x.split(",") if t.strip()]
    
    return [x]


@tool("get_company_info", description="Trả về thông tin cổ đông, lãnh đạo hoặc công ty con của mã cổ phiếu theo truy vấn.")
def get_company_info_tool(query: Optional[Dict[str, Any]] = None) -> str:
    try:
        info = get_company_info(query)
    except Exception as e:
        return f"Lỗi khi lấy thông tin công ty: {e}"

    if not info:
        return "Không có dữ liệu công ty."

    return to_pretty_json(info)


@tool("get_ohlcv", description="Trả về dữ liệu OHLCV cho mã cổ phiếu theo truy vấn.")
def get_ohlcv_tool(query: Optional[Dict[str, Any]] = None) -> str:
    try:
        records = get_ohlcv(query)
    except Exception as e:
        return f"Lỗi khi lấy OHLCV: {e}"

    if not records:
        return "Không có dữ liệu OHLCV."

    return to_pretty_json(records)


@tool("get_price_field", description="Trả về chuỗi thời gian của 1 trường giá.")
def get_price_field_tool(query: Optional[Dict[str, Any]] = None) -> str:
    try:
        records = get_price_field(query)
    except Exception as e:
        return f"Lỗi khi lấy trường giá: {e}"

    if not records:
        return "Không có dữ liệu trường giá."

    return to_pretty_json(records)


@tool("get_price_stat", description="Tính toán giá trị min/max/mean cho trường giá.")
def get_price_stat_tool(query: Optional[Dict[str, Any]] = None) -> str:
    stat = query.get("aggregate")
    if not stat:
        return "Thiếu thông tin aggregate (min/max/mean)."

    try:
        val = get_price_stat(query, stat)
    except Exception as e:
        return f"Lỗi khi tính thống kê giá: {e}"

    if val is None:
        return "Không có dữ liệu thống kê."

    try:
        return f"{stat}: {round(float(val), 2)}"
    except Exception:
        return f"{stat}: {val}"


@tool("get_aggregate_volume", description="Tính tổng khối lượng giao dịch trong khoảng thời gian.")
def get_aggregate_volume_tool(query: Optional[Dict[str, Any]] = None) -> str:
    try:
        total = get_aggregate_volume(query)
    except Exception as e:
        return f"Lỗi khi tính volume: {e}"

    if total is None:
        return "Không có dữ liệu khối lượng."

    return f"Tổng khối lượng: {int(total)}"


@tool("compare_volume", description="So sánh tổng volume giữa các mã cổ phiếu.")
def compare_volume_tool(query: Optional[Dict[str, Any]] = None) -> str:
    # allow tickers OR ticker + compare_with
    tickers = query.get("tickers") or _ensure_list(query.get("ticker")) or []
    compare_with = _ensure_list(query.get("compare_with"))
    if not tickers and not compare_with:
        return "Thiếu ticker(s) để so sánh."

    # compose compare list
    if not compare_with and len(tickers) > 1:
        # first is base, rest are compare_with
        base = tickers[0]
        compare_with = tickers[1:]
        tickers = [base]
    query["tickers"] = tickers

    try:
        results = compare_volume(query)
    except Exception as e:
        return f"Lỗi khi so sánh volume: {e}"

    if not results:
        return "Không có dữ liệu."

    return to_pretty_json(results)


@tool("get_min_open_across_tickers", description="Tìm mã có giá mở cửa thấp nhất.")
def get_min_open_across_tickers_tool(query: Optional[Dict[str, Any]] = None) -> str:
    try:
        result = get_min_open_across_tickers(query)
    except Exception as e:
        return f"Lỗi khi tìm min open: {e}"

    if not result:
        return "Không có dữ liệu."

    return to_pretty_json(result)


@tool("get_sma", description="Tính chỉ báo SMA cho các window size đã chỉ định.")
def get_sma_tool(query: Optional[Dict[str, Any]] = None) -> str:
    try:
        records = get_sma(query)
    except Exception as e:
        return f"Lỗi khi tính SMA: {e}"

    if not records:
        return "Không có dữ liệu SMA."

    return to_pretty_json(records)


@tool("get_rsi", description="Tính chỉ báo RSI cho các window size đã chỉ định.")
def get_rsi_tool(query: Optional[Dict[str, Any]] = None) -> str:
    try:
        records = get_rsi(query)
    except Exception as e:
        return f"Lỗi khi tính RSI: {e}"

    if not records:
        return "Không có dữ liệu RSI."

    return to_pretty_json(records)
