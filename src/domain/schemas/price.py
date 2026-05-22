from typing import Literal
from pydantic import BaseModel, Field, field_validator
from domain.entities.time_range import TimeRange, validate_ticker_list

_PRICE_FIELDS = {"open", "close", "volume", "ohlcv", "high", "low"}


class PriceQueryParams(TimeRange):
    query_type: Literal["price_query"] = "price_query"
    tickers: list[str] = Field(..., min_length=1, description="Stock ticker symbols")
    requested_field: str | None = Field("close", description="Field: open/close/volume/ohlcv")

    @field_validator("tickers")
    def validate_tickers(cls, v):
        return validate_ticker_list(v)

    @field_validator("requested_field")
    def validate_field(cls, v):
        if v is not None and v not in _PRICE_FIELDS:
            raise ValueError(f"requested_field must be one of {_PRICE_FIELDS}")
        return v


class PriceRecord(BaseModel):
    """A single date's price data point."""

    date: str
    open_price: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None


class PriceResult(BaseModel):
    """Per-ticker price query result."""

    ticker: str
    data: list[PriceRecord]
    start_date: str
    end_date: str


class ErrorResult(BaseModel):
    """Standard error response."""

    error: str


PriceQueryResponse = PriceResult | ErrorResult
