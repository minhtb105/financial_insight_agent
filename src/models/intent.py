from enum import Enum


class Intent(str, Enum):
    historical_prices = "historical_prices"      # generic price queries
    ohlcv = "ohlcv"                              # full OHLCV
    close_price = "close_price"                  # đóng
    open_price = "open_price"                    # mở
    min_open = "min_open"                        # mã có giá mở cửa thấp nhất (over a range)
    sum_volume = "sum_volume"                    # tổng volume
    compare_volume = "compare_volume"            # so sánh volume giữa tickers
    company_shareholders = "company_shareholders"
    company_subsidiaries = "company_subsidiaries"
    company_executives = "company_executives"    # lãnh đạo đang làm việc
    sma = "sma"                                  # SMA (window)
    rsi = "rsi"                                  # RSI (window)
    multiple_indicators = "multiple_indicators" # ví dụ SMA9 + SMA20
    other = "other"                              # fallback / biến thể
