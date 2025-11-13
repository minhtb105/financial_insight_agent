from langchain.tools import tool
from api_clients.vn_stock_client import VNStockClient


client = VNStockClient()

@tool
def get_company_info_tool(ticker: str) -> str:
    """Lấy thông tin cơ bản của công ty theo mã cổ phiếu."""
    info = client.get_company_info(ticker)
    if not info:
        return f"Không tìm thấy thông tin cho mã {ticker}"
    name = info.get("companyName", "")
    industry = info.get("industryName", "")
    return f"Công ty {name} hoạt động trong lĩnh vực {industry}."

@tool
def get_historical_prices_tool(ticker: str, start: str, end: str,
                               interval: str, months: int, window_size: int) -> str:
    """Truy xuất dữ liệu giá cổ phiếu từ ngày start đến end."""
    df = client.get_historical_prices(ticker, start, end, months, interval, window_size)
    
    return df.tail(5).to_string(index=False)
