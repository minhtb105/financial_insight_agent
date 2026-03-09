"""
Query Types

This module contains all query type enums consolidated into a single file
for better organization and easier maintenance.
"""

from enum import Enum


class QueryType(str, Enum):
    """Core query types for basic financial queries."""
    
    # Original query types
    price_query = "price_query"
    indicator_query = "indicator_query"
    company_query = "company_query"
    comparison_query = "comparison_query"
    ranking_query = "ranking_query"
    aggregate_query = "aggregate_query"


class ExtendedQueryType(str, Enum):
    """Extended query types for advanced financial analysis."""
    
    # Original types (for backward compatibility)
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


class AllQueryTypes(str, Enum):
    """All query types combined for comprehensive coverage."""
    
    # Core types
    price_query = "price_query"
    indicator_query = "indicator_query"
    company_query = "company_query"
    comparison_query = "comparison_query"
    ranking_query = "ranking_query"
    aggregate_query = "aggregate_query"
    
    # Extended types
    financial_ratio_query = "financial_ratio_query"
    news_sentiment_query = "news_sentiment_query"
    portfolio_query = "portfolio_query"
    alert_query = "alert_query"
    forecast_query = "forecast_query"
    sector_query = "sector_query"


# Backward compatibility aliases
QueryTypeEnum = QueryType
ExtendedQueryTypeEnum = ExtendedQueryType