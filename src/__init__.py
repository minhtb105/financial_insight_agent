"""
Financial Insight Agent

A comprehensive financial analysis agent that provides insights into Vietnamese stock market data.
This package includes advanced parsing, multiple query types, and enhanced agent capabilities.

Main Components:
- Domain: Core entities and business logic services
- Infrastructure: API clients and LLM components  
- Application: Agent orchestration and business logic
- Interfaces: CLI and HTTP interfaces for user interaction

Usage:
    from financial_insight_agent import domain, infrastructure, application, interfaces
    
    # Use domain services
    from domain.services import handle_price_query
    
    # Use infrastructure components
    from infrastructure.llm import QueryParser
    
    # Use application agents
    from application.agent import build_graph
    
    # Use interfaces
    from interfaces.http import app
"""

# Import main modules for easy access
from . import domain
from . import infrastructure  
from . import application
from . import interfaces

# Re-export key components for convenience
from .domain import (
    HistoricalQuery,
    handle_price_query,
    handle_indicator_query,
    handle_company_query,
    handle_compare_query,
    handle_ranking_query,
    handle_aggregate_query,
    handle_financial_ratio_query,
    handle_news_sentiment_query,
    handle_portfolio_query,
)

from .infrastructure import (
    VNStockClient,
    QueryParser,
    QueryPreprocessor,
)

from .application import (
    build_graph,
    build_enhanced_graph,
    EnhancedStockAgent,
)

from .interfaces import (
    ConsoleApp,
)

__version__ = "1.0.0"
__author__ = "Financial Insight Team"

__all__ = [
    # Main modules
    'domain',
    'infrastructure',
    'application', 
    'interfaces',
    
    # Domain components
    'HistoricalQuery',
    'handle_price_query',
    'handle_indicator_query',
    'handle_company_query',
    'handle_compare_query',
    'handle_ranking_query',
    'handle_aggregate_query',
    'handle_financial_ratio_query',
    'handle_news_sentiment_query',
    'handle_portfolio_query',
    
    # Infrastructure components
    'VNStockClient',
    'QueryParser',
    'QueryPreprocessor',
    
    # Application components
    'build_graph',
    'build_enhanced_graph',
    'EnhancedStockAgent',
    
    # Interface components
    'ConsoleApp',
]
