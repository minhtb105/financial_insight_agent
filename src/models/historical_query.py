from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from models.intent import Intent


class HistoricalQuery(BaseModel):
    intent: Intent = Field(..., description="Primary action / intent")
    tickers: List[str] = Field(default_factory=list, description="Uppercase tickers list, empty if none")
    requested_field: Optional[str] = Field(None, description="e.g. 'open','close','high','low','volume','ohlcv'")
    start: Optional[str] = Field(None, description="Start date YYYY-MM-DD or None")
    end: Optional[str] = Field(None, description="End date YYYY-MM-DD or None")
    months: Optional[int] = Field(None, description="If user asked for X months")
    weeks: Optional[int] = Field(None, description="If user asked for X weeks")
    days: Optional[int] = Field(None, description="If user asked for X days")
    interval: Optional[str] = Field(None, description="Data interval e.g. '1m','5m','30m','1d'")
    window_size: Optional[int] = Field(None, description="Window size for single indicator (e.g. 9 or 14)")
    indicators: Optional[List[str]] = Field(None, description="List of indicators requested, e.g. ['SMA','SMA'] or ['RSI']")
    indicator_params: Optional[Dict[str, Any]] = Field(None, description="Params per indicator, e.g. {'SMA':[9,20], 'RSI':14}")
    compare_with: Optional[List[str]] = Field(None, description="Tickers to compare with (for compare intents)")
    aggregate: Optional[str] = Field(None, description="Aggregation requested e.g. 'sum' (used for volume totals)")
    extra: Optional[Dict[str, Any]] = Field(None, description="Freeform extras if needed")
    
