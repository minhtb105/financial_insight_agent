from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class RankingQueryParams(BaseModel):
    query_type: str = "ranking_query"
    tickers: List[str] = Field(..., min_length=2, description="At least 2 tickers for ranking")
    requested_field: Optional[str] = Field("close", description="Field to rank by")
    aggregate: Optional[str] = Field("max", description="Aggregate: max/min/mean/latest")
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

    @field_validator('aggregate')
    def validate_aggregate(cls, v):
        allowed = {'max', 'min', 'mean', 'latest'}
        if v is not None and v not in allowed:
            raise ValueError(f"aggregate must be one of {allowed}")
        return v

    @field_validator('tickers')
    def validate_tickers(cls, v):
        if len(v) < 2:
            raise ValueError("ranking_query needs at least 2 tickers")
        return v

    model_config = {"from_attributes": True}