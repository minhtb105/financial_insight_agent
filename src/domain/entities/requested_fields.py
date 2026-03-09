"""
Requested Fields

This module contains all requested field enums consolidated into a single file
for better organization and easier maintenance.
"""

from enum import Enum


class RequestedField(str, Enum):
    """Core requested fields for basic financial queries."""
    
    # Original fields
    open = "open"
    close = "close"
    volume = "volume"
    ohlcv = "ohlcv"
    sma = "sma"
    rsi = "rsi"
    macd = "macd"
    shareholders = "shareholders"
    subsidiaries = "subsidiaries"
    executives = "executives"


class ExtendedRequestedField(str, Enum):
    """Extended requested fields for advanced financial analysis."""
    
    # Original fields (for backward compatibility)
    open = "open"
    close = "close"
    volume = "volume"
    ohlcv = "ohlcv"
    sma = "sma"
    rsi = "rsi"
    macd = "macd"
    shareholders = "shareholders"
    subsidiaries = "subsidiaries"
    executives = "executives"
    
    # Financial ratios
    pe = "pe"
    pb = "pb"
    roe = "roe"
    eps = "eps"
    roa = "roa"
    debt_to_equity = "debt_to_equity"
    current_ratio = "current_ratio"
    quick_ratio = "quick_ratio"
    dividend_yield = "dividend_yield"
    operating_margin = "operating_margin"
    net_margin = "net_margin"
    revenue_growth = "revenue_growth"
    eps_growth = "eps_growth"
    
    # Market data
    market_cap = "market_cap"
    beta = "beta"
    turnover_rate = "turnover_rate"
    foreign_ownership = "foreign_ownership"
    free_float = "free_float"
    institutional_ownership = "institutional_ownership"
    retail_ownership = "retail_ownership"
    
    # Extended indicators
    bollinger_bands = "bb"
    stochastic = "stochastic"
    adx = "adx"
    atr = "atr"
    obv = "obv"
    cci = "cci"
    williams_r = "williams_r"
    ultosc = "ultosc"
    mfi = "mfi"
    chaikin_osc = "chaikin_osc"
    vwap = "vwap"
    
    # News and sentiment
    news = "news"
    sentiment = "sentiment"
    social_volume = "social_volume"
    news_sentiment_score = "news_sentiment_score"
    social_sentiment_score = "social_sentiment_score"
    news_volume = "news_volume"
    
    # Portfolio
    portfolio_value = "portfolio_value"
    portfolio_performance = "portfolio_performance"
    portfolio_allocation = "portfolio_allocation"
    portfolio_risk = "portfolio_risk"
    portfolio_diversification = "portfolio_diversification"
    portfolio_turnover = "portfolio_turnover"
    
    # Alerts
    price_alert = "price_alert"
    volume_alert = "volume_alert"
    technical_alert = "technical_alert"
    news_alert = "news_alert"
    sentiment_alert = "sentiment_alert"
    portfolio_alert = "portfolio_alert"
    
    # Forecasts
    price_forecast = "price_forecast"
    trend_analysis = "trend_analysis"
    support_resistance = "support_resistance"
    momentum_forecast = "momentum_forecast"
    volatility_forecast = "volatility_forecast"
    risk_forecast = "risk_forecast"
    
    # Sectors
    sector_performance = "sector_performance"
    sector_allocation = "sector_allocation"
    sector_rotation = "sector_rotation"
    industry_analysis = "industry_analysis"
    peer_comparison = "peer_comparison"
    sector_sentiment = "sector_sentiment"


class AllRequestedFields(str, Enum):
    """All requested fields combined for comprehensive coverage."""
    
    # Core fields
    open = "open"
    close = "close"
    volume = "volume"
    ohlcv = "ohlcv"
    sma = "sma"
    rsi = "rsi"
    macd = "macd"
    shareholders = "shareholders"
    subsidiaries = "subsidiaries"
    executives = "executives"
    
    # Extended fields
    pe = "pe"
    pb = "pb"
    roe = "roe"
    eps = "eps"
    roa = "roa"
    debt_to_equity = "debt_to_equity"
    current_ratio = "current_ratio"
    quick_ratio = "quick_ratio"
    dividend_yield = "dividend_yield"
    operating_margin = "operating_margin"
    net_margin = "net_margin"
    revenue_growth = "revenue_growth"
    eps_growth = "eps_growth"
    
    market_cap = "market_cap"
    beta = "beta"
    turnover_rate = "turnover_rate"
    foreign_ownership = "foreign_ownership"
    free_float = "free_float"
    institutional_ownership = "institutional_ownership"
    retail_ownership = "retail_ownership"
    
    bollinger_bands = "bb"
    stochastic = "stochastic"
    adx = "adx"
    atr = "atr"
    obv = "obv"
    cci = "cci"
    williams_r = "williams_r"
    ultosc = "ultosc"
    mfi = "mfi"
    chaikin_osc = "chaikin_osc"
    vwap = "vwap"
    
    news = "news"
    sentiment = "sentiment"
    social_volume = "social_volume"
    news_sentiment_score = "news_sentiment_score"
    social_sentiment_score = "social_sentiment_score"
    news_volume = "news_volume"
    
    portfolio_value = "portfolio_value"
    portfolio_performance = "portfolio_performance"
    portfolio_allocation = "portfolio_allocation"
    portfolio_risk = "portfolio_risk"
    portfolio_diversification = "portfolio_diversification"
    portfolio_turnover = "portfolio_turnover"
    
    price_alert = "price_alert"
    volume_alert = "volume_alert"
    technical_alert = "technical_alert"
    news_alert = "news_alert"
    sentiment_alert = "sentiment_alert"
    portfolio_alert = "portfolio_alert"
    
    price_forecast = "price_forecast"
    trend_analysis = "trend_analysis"
    support_resistance = "support_resistance"
    momentum_forecast = "momentum_forecast"
    volatility_forecast = "volatility_forecast"
    risk_forecast = "risk_forecast"
    
    sector_performance = "sector_performance"
    sector_allocation = "sector_allocation"
    sector_rotation = "sector_rotation"
    industry_analysis = "industry_analysis"
    peer_comparison = "peer_comparison"
    sector_sentiment = "sector_sentiment"


# Backward compatibility aliases
RequestedFieldEnum = RequestedField
ExtendedRequestedFieldEnum = ExtendedRequestedField