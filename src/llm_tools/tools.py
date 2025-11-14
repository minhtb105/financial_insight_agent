from langchain.tools import tool
from data.indicators import (
    get_company_info,
    get_ohlcv,
    get_price_stat,
    get_aggregate_volume,
    compare_volume,
    get_sma,
    get_rsi,
)
from typing import Dict, Any, Optional


@tool("get_company_info", return_direct=True)
def get_company_info_tool(query: Dict[str, Any]) -> str:
    """Lấy thông tin công ty theo schema query."""
    try:
        info = get_company_info(query)
    except Exception as e:
        return f"❌ Lỗi khi lấy thông tin công ty: {e}"
    
    # Tuỳ thuộc vào requested_field, info có thể là shareholders, executives, subsidiaries...
    if isinstance(info, list):
        return "\n".join(str(x) for x in info)
    
    return str(info)

@tool("get_ohlcv", return_direct=True)
def get_ohlcv_tool(query: Dict[str, Any]) -> str:
    """Lấy dữ liệu OHLCV theo schema query."""
    try:
        df = get_ohlcv(query)
    except Exception as e:
        return f"Lỗi khi lấy OHLCV: {e}"

    if df is None or df.empty:
        return "Không có dữ liệu OHLCV."

    try:
        return df.tail(5).to_string(index=False)
    except Exception:
        return df.to_string(index=False)


@tool("get_price_stat", return_direct=True)
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

@tool("get_aggregate_volume", return_direct=True)
def get_aggregate_volume_tool(query: Dict[str, Any]) -> str:
    """Tính tổng khối lượng giao dịch."""
    try:
        val = get_aggregate_volume(query)
    except Exception as e:
        return f"❌ Lỗi khi tính tổng volume: {e}"

    if val is None:
        return "Không có dữ liệu khối lượng."
    
    return f"Tổng khối lượng: {int(val)}"

@tool("compare_volume", return_direct=True)
def compare_volume_tool(query: Dict[str, Any]) -> str:
    """So sánh khối lượng giao dịch giữa các mã."""
    try:
        result = compare_volume(query)
    except Exception as e:
        return f"Lỗi khi so sánh volume: {e}"

    if not result:
        return "Không có dữ liệu so sánh."

    lines = []
    for ticker, vol in result.items():
        lines.append(f"{ticker}: {int(vol)}")
        
    return "\n".join(lines)

@tool("get_sma", return_direct=True)
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

@tool("get_rsi", return_direct=True)
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
