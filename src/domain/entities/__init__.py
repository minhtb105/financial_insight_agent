"""
Domain Entities

This module contains all the domain entities used throughout the financial insight agent.
These entities represent the core data structures and business concepts.
"""

# Core Entities
from .historical_query import HistoricalQuery
from .interval import Interval

# Extended Entities
from .extended_query_type import ExtendedQueryType
from .extended_requested_field import ExtendedRequestedField

__all__ = [
    # Core Entities
    'HistoricalQuery',
    'Interval',
    
    # Extended Entities
    'ExtendedQueryType',
    'ExtendedRequestedField',
]
