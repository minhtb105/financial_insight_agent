from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class PriceQueryParams(BaseModel):
    query_type: str = "price_query"
    tickers: List[str] = Field(..., min_length=1, description="Stock ticker symbols")
    requested_field: Optional[str] = Field("close", description="Field: open/close/volume/ohlcv")
    start: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    end: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    days: Optional[int] = Field(None, ge=1, description="Number of days")
    weeks: Optional[int] = Field(None, ge=1, description="Number of weeks")
    months: Optional[int] = Field(None, ge=1, description="Number of months")
    years: Optional[int] = Field(None, ge=1, description="Number of years")

    @field_validator('requested_field')
    def validate_field(cls, v):
        allowed = {'open', 'close', 'volume', 'ohlcv', 'high', 'low'}
        if v is not None and v not in allowed:
            raise ValueError(f"requested_field must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}