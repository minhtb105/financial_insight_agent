from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from models.query_type import QueryType
from models.requested_field import RequestedField
from models.interval import Interval


class HistoricalQuery(BaseModel):
    query_type: QueryType = Field(..., description="6 loại nhiệm vụ agent cần xử lý")

    requested_field: Optional[RequestedField] = Field(
        None, description="Field cụ thể: open_price, volume, sma, shareholders,…"
    )

    tickers: List[str] = Field(default_factory=list, description="Danh sách mã cổ phiếu")

    start: Optional[str] = None
    end: Optional[str] = None
    months: Optional[int] = None
    weeks: Optional[int] = None
    days: Optional[int] = None
    interval: Optional[Interval] = None

    indicator_params: Optional[Dict[str, Any]] = None

    compare_with: Optional[List[str]] = None
    aggregate: Optional[str] = None

    extra: Optional[Dict[str, Any]] = None
    