from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SectorQueryParams(BaseModel):
    query_type: str = "sector_query"
    sector: str = Field(..., description="Sector name (e.g. banking, real estate)")
    metric: Optional[str] = Field("performance")
    timeframe: Optional[str] = Field("1w")

    @field_validator('metric')
    def validate_metric(cls, v):
        allowed = {'performance', 'volume'}
        if v is not None and v not in allowed:
            raise ValueError(f"metric must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}