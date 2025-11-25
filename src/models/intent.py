from enum import Enum


# === 1) INTENT TWO-LEVEL STRUCTURE ===

class Intent(str, Enum):
    historical_prices = "historical_prices" 
    technical_indicator = "technical_indicator" 
    company_info = "company_info" 

class RequestedField(str, Enum):
    # Historical price fields
    open_price = "open_price"      
    close_price = "close_price"    
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
    