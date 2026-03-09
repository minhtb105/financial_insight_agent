from enum import Enum


class ExtendedQueryType(str, Enum):
    """Extended query types for new financial question categories."""
    
    # Existing types (for backward compatibility)
    price_query = "price_query"
    indicator_query = "indicator_query"
    company_query = "company_query"
    ranking_query = "ranking_query"
    comparison_query = "comparison_query"
    aggregate_query = "aggregate_query"
    
    # New financial ratio query type
    financial_ratio_query = "financial_ratio_query"
    
    # News and sentiment query type
    news_sentiment_query = "news_sentiment_query"
    
    # Portfolio query type
    portfolio_query = "portfolio_query"
    
    # Alert and monitoring query type
    alert_query = "alert_query"
    
    # Forecast and trend query type
    forecast_query = "forecast_query"
    
    # Sector and group query type
    sector_query = "sector_query"