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
from typing import Dict, Any
import json


def to_pretty_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)

@tool("get_company_info", description="Trả về thông tin cổ đông, lãnh đạo hoặc công ty con của mã cổ phiếu theo truy vấn.")
def get_company_info_tool(query: Dict[str, Any]) -> str:
    """Lấy thông tin công ty theo schema query."""
    try:
        info = get_company_info(query)
    except Exception as e:
        return f"Lỗi khi lấy thông tin công ty: {e}"
    
    if not info:
        return "Không có dữ liệu công ty."
    
    # Tuỳ thuộc vào requested_field, info có thể là shareholders, executives, subsidiaries...
    return to_pretty_json(info)

@tool("get_ohlcv", description="Trả về dữ liệu OHLCV (giá mở cửa, đóng cửa, cao nhất, thấp nhất, khối lượng) cho mã cổ phiếu theo truy vấn.")
def get_ohlcv_tool(query: Dict[str, Any]) -> str:
    """Lấy dữ liệu OHLCV theo schema query."""
    try:
        records = get_ohlcv(query)
    except Exception as e:
        return f"Lỗi khi lấy OHLCV: {e}"

    if not records:
        return "Không có dữ liệu OHLCV."

    return to_pretty_json(records)

@tool("get_price_stat",  description="Tính toán giá trị min, max hoặc trung bình cho giá mở cửa hoặc đóng cửa của mã cổ phiếu.")
def get_price_stat_tool(query: Dict[str, Any]) -> str:
    """Lấy giá trị thống kê (min/max/mean) cho trường giá."""
    try:
        stat = query.get("aggregate")
        if stat is None:
            return "Thiếu thông tin aggregate (min/max/mean)."

        val = get_price_stat(query, stat)
    except Exception as e:
        return f"Lỗi khi tính thống kê giá: {e}"

    if val is None:
        return "Không có dữ liệu thống kê."
    
    if isinstance(val, float):
        return f"{stat}: {round(val, 2)}"
    
    return f"{stat}: {val}"

@tool("get_aggregate_volume", description="Tính tổng khối lượng giao dịch của mã cổ phiếu trong khoảng thời gian truy vấn.")
def get_aggregate_volume_tool(query: Dict[str, Any]) -> str:
    """Tính tổng khối lượng giao dịch."""
    try:
        val = get_aggregate_volume(query)
    except Exception as e:
        return f"Lỗi khi tính tổng volume: {e}"

    if val is None:
        return "Không có dữ liệu khối lượng."
    
    return f"Tổng khối lượng: {int(val)}"

@tool("compare_volume", description="So sánh tổng khối lượng giao dịch giữa nhiều mã cổ phiếu trong cùng khoảng thời gian.")
def compare_volume_tool(query: Dict[str, Any]) -> str:
    """So sánh khối lượng giao dịch giữa các mã."""
    try:
        result = compare_volume(query)
    except Exception as e:
        return f"Lỗi khi so sánh volume: {e}"

    if not result:
        return "Không có dữ liệu so sánh."

    return to_pretty_json(result)

@tool("get_sma", description="Tính chỉ báo SMA (Simple Moving Average) cho mã cổ phiếu với các window size được chỉ định.")
def get_sma_tool(query: dict) -> str:
    """Tính SMA cho mã cổ phiếu."""
    try:
        result = get_sma(query)
    except Exception as e:
        return f"Lỗi khi tính SMA: {e}"

    if not result:
        return "Không có dữ liệu SMA."

    # Format: SMA9: 12.34, SMA20: 13.45
    out = []
    for k, v in result.items():
        try:
            out.append(f"{k}: {round(float(v), 2)}")
        except Exception:
            out.append(f"{k}: {v}")
            
    return ", ".join(out)

@tool("get_rsi", description="Tính chỉ báo RSI (Relative Strength Index) cho mã cổ phiếu với các window size được chỉ định.")
def get_rsi_tool(query: Dict[str, Any]) -> str:
    """Tính RSI cho mã cổ phiếu."""
    try:
        result = get_rsi(query)
    except Exception as e:
        return f"Lỗi khi tính RSI: {e}"

    if not result:
        return "Không có dữ liệu RSI."

    out = []
    for k, v in result.items():
        try:
            out.append(f"{k}: {round(float(v), 2)}")
        except Exception:
            out.append(f"{k}: {v}")
            
    return ", ".join(out)

@tool("get_price_field", description="Trả về chuỗi thời gian của một trường giá (open, close, high, low, volume) cho mã cổ phiếu.")
def get_price_field_tool(query: Dict[str, Any]) -> str:
    """Lấy chuỗi thời gian của một trường giá cụ thể theo schema query."""
    try:
        df = get_price_field(query)
    except Exception as e:
        return f"Lỗi khi lấy trường giá: {e}"
    
    if df is None or df.empty:
        return "Không có dữ liệu trường giá."
    
    return df.to_string(index=False)

@tool("get_min_open_across_tickers", description="Tìm mã có giá mở cửa thấp nhất trong danh sách tickers trong khoảng thời gian truy vấn.")
def get_min_open_across_tickers_tool(query: Dict[str, Any]) -> str:
    """Tìm mã có giá mở cửa thấp nhất trong danh sách tickers."""
    try:
        result = get_min_open_across_tickers(query)
    except Exception as e:
        return f"Lỗi khi tìm mã có open thấp nhất: {e}"
    
    if not result:
        return "Không có dữ liệu."
    
    return to_pretty_json(result)
