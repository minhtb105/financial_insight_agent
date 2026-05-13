from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class AlertQueryParams(BaseModel):
    query_type: str = "alert_query"
    tickers: List[str] = Field(..., min_length=1)
    threshold: float = Field(..., gt=0, description="Price threshold value")
    condition: Optional[str] = Field("above")
    timeframe: Optional[str] = Field("1d")

    @field_validator('condition')
    def validate_condition(cls, v):
        allowed = {'above', 'below'}
        if v is not None and v not in allowed:
            raise ValueError(f"condition must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}