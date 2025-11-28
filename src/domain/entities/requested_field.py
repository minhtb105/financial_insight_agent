from enum import Enum


class RequestedField(str, Enum):
    # Historical price fields
    open = "open"
    close = "close"
    volume = "volume"
    ohlcv = "ohlcv"

    # Technical indicators
    sma = "sma"
    rsi = "rsi"
    macd = "macd"

    # Company data
    shareholders = "shareholders"
    subsidiaries = "subsidiaries"
    executives = "executives"
