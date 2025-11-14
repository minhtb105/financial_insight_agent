from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from models.intent import Intent, RequestedField


class HistoricalQuery(BaseModel):
    """
    intent = historical_prices → required: tickers + requested_field in {ohlcv,open_price,...}
    intent = technical_indicator → required: tickers + requested_field in {sma,rsi}
    intent = company_info → required: tickers + requested_field in {executives,shareholders,subsidiaries}
    """
    intent: Intent = Field(..., description="Action category (historical_prices / technical_indicator / company_info)")
    requested_field: Optional[RequestedField] = Field(
        None,
        description="Specific field requested: open_price, sma, shareholders, ..."
    )
    tickers: List[str] = Field(default_factory=list, description="Ticker symbols (uppercase)")
    
    # Time ranges
    start: Optional[str] = Field(None, description="Start date YYYY-MM-DD or None")
    end: Optional[str] = Field(None, description="End date YYYY-MM-DD or None")
    months: Optional[int] = Field(None, description="If user asked for X months")
    weeks: Optional[int] = Field(None, description="If user asked for X weeks")
    days: Optional[int] = Field(None, description="If user asked for X days")
    
    interval: Optional[str] = Field(None, description="Data interval e.g. '1m','5m','30m','1d'")
    
    # Technical indicator parameters
    window_size: Optional[int] = Field(None, description="Window size for single indicator (e.g. 9 or 14)")
    indicators: Optional[List[str]] = Field(None, description="List of indicators requested, e.g. ['SMA','SMA'] or ['RSI']")
    indicator_params: Optional[Dict[str, Any]] = Field(None, description="Params per indicator, e.g. {'SMA':[9,20], 'RSI':14}")
    
    # Comparison and aggregation
    compare_with: Optional[List[str]] = Field(None, description="Tickers to compare with (for compare intents)")
    aggregate: Optional[str] = Field(None, description="Aggregation requested e.g. 'sum' (used for volume totals)")
    extra: Optional[Dict[str, Any]] = Field(None, description="Freeform extras if needed")
    