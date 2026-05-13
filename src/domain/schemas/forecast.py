from typing import List, Optional
from pydantic import BaseModel, Field


class ForecastQueryParams(BaseModel):
    query_type: str = "forecast_query"
    tickers: List[str] = Field(..., min_length=1)
    timeframe: Optional[str] = Field("1w")
    model: Optional[str] = Field(None)

    model_config = {"from_attributes": True}