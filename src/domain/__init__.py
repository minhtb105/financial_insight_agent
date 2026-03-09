"""
Financial Insight Agent - Domain Layer

This module contains the core domain entities and services for the financial insight agent.
"""

# Entities
from .entities.historical_query import HistoricalQuery
from .entities.interval import Interval

# Extended Entities
from .entities.extended_query_type import ExtendedQueryType
from .entities.extended_requested_field import ExtendedRequestedField

# Services
from .services.market.price_service import handle_price_query
from .services.market.indicator_service import handle_indicator_query
from .services.company.company_service import handle_company_query
from .services.market.compare_service import handle_compare_query
from .services.financial.ranking_service import handle_ranking_query
from .services.financial.aggregate_service import handle_aggregate_query

# Extended Services
from .services.financial.financial_ratio_service import handle_financial_ratio_query
from .services.portfolio.news_sentiment_service import handle_news_sentiment_query
from .services.portfolio.portfolio_service import handle_portfolio_query

__all__ = [
    # Core Entities
    'HistoricalQuery',
    'Interval', 
    
    # Extended Entities
    'ExtendedQueryType',
    'ExtendedRequestedField',
    
    # Core Services
    'handle_price_query',
    'handle_indicator_query', 
    'handle_company_query',
    'handle_compare_query',
    'handle_ranking_query',
    'handle_aggregate_query',
    
    # Extended Services
    'handle_financial_ratio_query',
    'handle_news_sentiment_query',
    'handle_portfolio_query',
]
