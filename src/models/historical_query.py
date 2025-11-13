from pydantic import BaseModel, Field 
from typing import Optional


class HistoricalQuery(BaseModel):
    intent: str = Field(..., description="One of: 'historical_prices', 'company_info'")
    ticker: Optional[str] = Field(None, description="Stock ticker, uppercase (eg. VCB)")
    start: Optional[str] = Field(None, description="Start date in YYYY-MM-DD or null")
    end: Optional[str] = Field(None, description="End date in YYYY-MM-DD or null")
    months: Optional[int] = Field(None, description="If user asked for X months")
    interval: Optional[str] = Field(None, description="Data interval e.g. '1m', '30m', '1h'")
    window_size: Optional[int] = Field(None, description="Window size for SMA/RSI")
