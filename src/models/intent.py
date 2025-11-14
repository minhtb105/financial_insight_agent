from enum import Enum


# === 1) INTENT TWO-LEVEL STRUCTURE ===

class Intent(str, Enum):
    historical_prices = "historical_prices" # lấy dữ liệu giá quá khứ
    technical_indicator = "technical_indicator" # SMA, RSI, MACD, ...
    company_info = "company_info" # lãnh đạo, cổ đông, công ty con

# === 2) REQUESTED FIELD (CỤ THỂ MUỐN LẤY GÌ) ===
# Parser sẽ map các câu hỏi sang requested_field
# ví dụ: "giá đóng" → "close_price"

class RequestedField(str, Enum):
    # Historical price fields
    open_price = "open_price"       # Giá mở cửa
    close_price = "close_price"     # Giá đóng cửa
    volume = "volume"               # Khối lượng giao dịch
    ohlcv = "ohlcv"                 # Giá trị OHLCV đầy đủ

    # Technical indicators
    sma = "sma" # Chỉ báo SMA
    rsi = "rsi" # Chỉ báo RSI
    macd = "macd" # Chỉ báo MACD

    # Company data
    shareholders = "shareholders" # Danh sách cổ đông lớn
    subsidiaries = "subsidiaries" # Danh sách ban lãnh đạo
    executives = "executives" # Danh sách công ty con
    