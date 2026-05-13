from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CompanyQueryParams(BaseModel):
    query_type: str = "company_query"
    tickers: List[str] = Field(..., min_length=1)
    requested_field: Optional[str] = Field("shareholders")

    @field_validator('requested_field')
    def validate_field(cls, v):
        allowed = {'shareholders', 'executives', 'subsidiaries'}
        if v is not None and v not in allowed:
            raise ValueError(f"requested_field must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}