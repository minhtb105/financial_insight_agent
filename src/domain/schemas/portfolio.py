from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class PortfolioQueryParams(BaseModel):
    query_type: str = "portfolio_query"
    requested_field: Optional[str] = Field(None)
    portfolio: Optional[Dict[str, int]] = Field(None, description="Holdings {ticker: quantity}")
    tickers: Optional[List[str]] = Field(None, description="Optional ticker filter")

    @field_validator('requested_field')
    def validate_field(cls, v):
        allowed = {
            'portfolio_value', 'portfolio_performance', 'portfolio_allocation',
            'portfolio_summary', 'performance', 'sector_allocation',
            'portfolio_risk', 'portfolio_diversification', 'portfolio_turnover'
        }
        if v is not None and v not in allowed:
            raise ValueError(f"requested_field must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}