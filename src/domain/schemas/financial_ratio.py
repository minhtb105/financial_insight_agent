from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class FinancialRatioQueryParams(BaseModel):
    query_type: str = "financial_ratio_query"
    tickers: List[str] = Field(..., min_length=1)
    requested_field: Optional[str] = Field("pe")
    period: Optional[str] = Field(None, description="quarter/year")
    quarter: Optional[int] = Field(None, ge=1, le=4)
    year: Optional[int] = Field(None)

    @field_validator('requested_field')
    def validate_field(cls, v):
        allowed = {
            'pe', 'pb', 'roe', 'eps', 'roa', 'debt_to_equity',
            'current_ratio', 'quick_ratio', 'dividend_yield',
            'operating_margin', 'net_margin', 'revenue_growth', 'eps_growth',
            'profit_margin', 'asset_turnover', 'financial_ratio'
        }
        if v is not None and v not in allowed:
            raise ValueError(f"requested_field must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}