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
    close_price = "close_price"
    open_price = "open_price"
    high_price = "high_price"
    low_price = "low_price"
    ohlcv = "ohlcv"
    volume = "volume"

    # Technical indicators
    sma = "sma" # SMA window
    rsi = "rsi" # RSI window
    macd = "macd" # MACD

    # Company data
    shareholders = "shareholders"
    subsidiaries = "subsidiaries"
    executives = "executives"
    