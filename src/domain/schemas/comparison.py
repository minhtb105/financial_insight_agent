from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ComparisonQueryParams(BaseModel):
    query_type: str = "comparison_query"
    tickers: List[str] = Field(..., min_length=1, description="Main group of tickers")
    compare_with: List[str] = Field(..., min_length=1, description="Reference group of tickers")
    requested_field: Optional[str] = Field("close")
    start: Optional[str] = None
    end: Optional[str] = None
    days: Optional[int] = Field(None, ge=1)
    weeks: Optional[int] = Field(None, ge=1)
    months: Optional[int] = Field(None, ge=1)

    @field_validator('requested_field')
    def validate_field(cls, v):
        allowed = {'open', 'close', 'volume', 'high', 'low'}
        if v is not None and v not in allowed:
            raise ValueError(f"requested_field must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}