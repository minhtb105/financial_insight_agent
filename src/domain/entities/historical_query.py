"""
Historical Query Entity

This module defines the HistoricalQuery data structure that represents
a parsed financial query with all its components and metadata.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class HistoricalQuery(BaseModel):
    """
    Represents a parsed historical financial query.
    
    This entity contains all the information needed to execute a financial query,
    including tickers, time parameters, requested fields, and query metadata.
    """
    
    # Core query information
    tickers: List[str] = Field(..., description="List of stock tickers")
    query_type: str = Field(..., description="Type of query (price, indicator, etc.)")
    requested_field: Optional[str] = Field(None, description="Specific field requested")
    
    # Time parameters
    start: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    days: Optional[int] = Field(None, description="Number of days")
    weeks: Optional[int] = Field(None, description="Number of weeks")
    months: Optional[int] = Field(None, description="Number of months")
    years: Optional[int] = Field(None, description="Number of years")
    
    # Query-specific parameters
    indicator_params: Optional[Dict[str, Any]] = Field(None, description="Indicator parameters")
    aggregate: Optional[str] = Field(None, description="Aggregation function")
    compare_with: Optional[List[str]] = Field(None, description="Tickers to compare with")
    
    # Financial ratio parameters
    period: Optional[str] = Field(None, description="Financial period (quarter, month, year)")
    quarter: Optional[int] = Field(None, description="Quarter number (1-4)")
    year: Optional[int] = Field(None, description="Year")
    
    # Sentiment parameters
    sentiment: Optional[Dict[str, Any]] = Field(None, description="Sentiment scores (can be nested per ticker)")
    
    # Metadata
    confidence: Optional[float] = Field(None, description="Parsing confidence score")
    timestamp: Optional[str] = Field(None, description="Query timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "tickers": ["VCB", "HPG"],
                "query_type": "price_query",
                "requested_field": "close",
                "days": 7,
                "confidence": 0.95
            }
        }
    
    @field_validator('tickers')
    def validate_tickers(cls, v):
        """Validate tickers list."""
        # For portfolio queries, tickers can be empty
        if not v:
            # Allow empty tickers for portfolio queries
            return v
        
        for ticker in v:
            if not isinstance(ticker, str) or not ticker.isalpha():
                raise ValueError(f"Invalid ticker: {ticker}")
        return v
    
    @field_validator('query_type')
    def validate_query_type(cls, v):
        """Validate query type."""
        valid_types = [
            'price_query', 'indicator_query', 'company_query',
            'comparison_query', 'ranking_query', 'aggregate_query',
            'financial_ratio_query', 'news_sentiment_query',
            'portfolio_query', 'alert_query', 'forecast_query', 'sector_query'
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid query type: {v}")
        return v
    
    @field_validator('days', 'weeks', 'months', 'years')
    def validate_time_params(cls, v):
        """Validate time parameters."""
        if v is not None and v <= 0:
            raise ValueError("Time parameters must be positive")
        return v
    
    @field_validator('confidence')
    def validate_confidence(cls, v):
        """Validate confidence score."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Confidence must be between 0 and 1")
        return v
    
    def get_time_range(self) -> Dict[str, str]:
        """
        Get the time range for the query.
        
        Returns:
            Dict with start and end dates
        """
        if self.start and self.end:
            return {"start": self.start, "end": self.end}
        
        # Calculate based on time parameters
        end_date = datetime.now()
        start_date = end_date
        
        if self.days:
            start_date = end_date.replace(day=end_date.day - self.days)
        elif self.weeks:
            start_date = end_date.replace(day=end_date.day - (self.weeks * 7))
        elif self.months:
            start_date = end_date.replace(month=end_date.month - self.months)
        elif self.years:
            start_date = end_date.replace(year=end_date.year - self.years)
        
        return {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }
    
    def is_comparison_query(self) -> bool:
        """Check if this is a comparison query."""
        return self.query_type == 'comparison_query' and bool(self.compare_with)
    
    def is_ranking_query(self) -> bool:
        """Check if this is a ranking query."""
        return self.query_type == 'ranking_query' and len(self.tickers) > 1
    
    def is_aggregate_query(self) -> bool:
        """Check if this is an aggregate query."""
        return self.query_type == 'aggregate_query' and bool(self.aggregate)
    
    def get_indicator_types(self) -> List[str]:
        """Get list of indicator types requested."""
        if not self.indicator_params:
            return []
        return list(self.indicator_params.keys())
    
    def get_indicator_params_for_type(self, indicator_type: str) -> Any:
        """Get parameters for a specific indicator type."""
        if not self.indicator_params:
            return []
        params = self.indicator_params.get(indicator_type, [])
        # Handle both list and dict types
        if isinstance(params, list):
            return params
        elif isinstance(params, dict):
            return params
        else:
            return [params] if params is not None else []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump(exclude_none=True)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# Backward compatibility
HistoricalQueryModel = HistoricalQuery