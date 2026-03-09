"""
Domain Services

This module contains all the domain services that implement the business logic
for handling different types of financial queries.
"""

# Base Services
from .base.time_processor import TimeProcessor, process_service_time_params

# Company Services
from .company.company_service import handle_company_query

# Financial Services
from .financial.financial_ratio_service import handle_financial_ratio_query
from .financial.aggregate_service import handle_aggregate_query
from .financial.ranking_service import handle_ranking_query

# Market Services
from .market.price_service import handle_price_query
from .market.indicator_service import handle_indicator_query
from .market.compare_service import handle_compare_query

# Portfolio Services
from .portfolio.portfolio_service import handle_portfolio_query
from .portfolio.news_sentiment_service import handle_news_sentiment_query

__all__ = [
    # Base Services
    'TimeProcessor',
    'process_service_time_params',
    
    # Company Services
    'handle_company_query',
    
    # Financial Services
    'handle_financial_ratio_query',
    'handle_aggregate_query',
    'handle_ranking_query',
    
    # Market Services
    'handle_price_query',
    'handle_indicator_query',
    'handle_compare_query',
    
    # Portfolio Services
    'handle_portfolio_query',
    'handle_news_sentiment_query',
]
