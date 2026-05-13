from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class IndicatorQueryParams(BaseModel):
    query_type: str = "indicator_query"
    tickers: List[str] = Field(..., min_length=1)
    requested_field: Optional[str] = Field("sma")
    indicator_params: Optional[Dict[str, Any]] = Field(None, description="e.g. {sma: [20], rsi: [14], macd: [(12,26)]}")
    start: Optional[str] = None
    end: Optional[str] = None
    days: Optional[int] = Field(None, ge=1)
    weeks: Optional[int] = Field(None, ge=1)
    months: Optional[int] = Field(None, ge=1)

    @field_validator('requested_field')
    def validate_field(cls, v):
        allowed = {'sma', 'rsi', 'macd', 'bb', 'stochastic', 'adx', 'atr', 'obv', 'cci', 'williams_r', 'ultosc', 'mfi', 'vwap'}
        if v is not None and v not in allowed:
            raise ValueError(f"requested_field must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}