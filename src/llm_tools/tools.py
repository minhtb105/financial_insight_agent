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


@tool
def get_company_info_tool(query: dict) -> str:
    """Lấy thông tin công ty theo schema query."""
    info = get_company_info(query)
    if not info:
        return f"Không tìm thấy thông tin cho mã {query.get('tickers', [''])[0]}"
    
    # Tuỳ thuộc vào requested_field, info có thể là shareholders, executives, subsidiaries...
    if isinstance(info, list):
        return "\n".join(str(x) for x in info)
    
    return str(info)

@tool
def get_ohlcv_tool(query: dict) -> str:
    """Lấy dữ liệu OHLCV theo schema query."""
    df = get_ohlcv(query)
    if df is None or df.empty:
        return "Không có dữ liệu OHLCV."
            
    return df.tail(5).to_string(index=False)

@tool
def get_price_stat_tool(query: dict, stat: str) -> str:
    """Lấy giá trị thống kê (min/max/mean) cho trường giá."""
    val = get_price_stat(query, stat)
    
    if val is None:
        return "Không có dữ liệu thống kê."
    
    return f"{stat} {query.get('requested_field', '')}: {val}"

@tool
def get_aggregate_volume_tool(query: dict) -> str:
    """Tính tổng khối lượng giao dịch."""
    val = get_aggregate_volume(query)
    if val is None:
        return "Không có dữ liệu khối lượng."
    
    return f"Tổng khối lượng: {val}"

@tool
def compare_volume_tool(query: dict) -> str:
    """So sánh khối lượng giao dịch giữa các mã."""
    result = compare_volume(query)
    if not result:
        return "Không có dữ liệu so sánh."
    
    return "\n".join(f"{ticker}: {vol}" for ticker, vol in result.items())

@tool
def get_sma_tool(query: dict) -> str:
    """Tính SMA cho mã cổ phiếu."""
    result = get_sma(query)
    if not result:
        return "Không có dữ liệu SMA."
    
    return ", ".join(f"{k}: {v}" for k, v in result.items())

@tool
def get_rsi_tool(query: dict) -> str:
    """Tính RSI cho mã cổ phiếu."""
    result = get_rsi(query)
    if not result:
        return "Không có dữ liệu RSI."
    
    return ", ".join(f"{k}: {v}" for k, v in result.items())
