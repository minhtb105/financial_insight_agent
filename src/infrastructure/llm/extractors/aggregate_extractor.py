import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class AggregateParams(BaseModel):
    tickers: List[str] = Field(..., description="Stock ticker symbols, e.g. ['VCB']")
    aggregate: str = Field(
        "mean", description="Aggregation: mean, sum, median, std, min, max"
    )
    days: Optional[int] = Field(None, description="Number of days")
    weeks: Optional[int] = Field(None, description="Number of weeks")
    months: Optional[int] = Field(None, description="Number of months")
    requested_field: str = Field(
        "close", description="Field: open, close, volume, high, low"
    )


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi tổng hợp dữ liệu chứng khoán.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- aggregate: hàm tổng hợp (mean/sum/median/std/min/max)
- days/weeks/months: khoảng thời gian
- requested_field: trường dữ liệu (open/close/volume/high/low)

Ví dụ:
- "Tổng khối lượng giao dịch của HPG trong 1 tuần"
  -> {{"tickers": ["HPG"], "aggregate": "sum", "weeks": 1, "requested_field": "volume"}}
- "Giá đóng trung bình của VCB trong 10 ngày"
  -> {{"tickers": ["VCB"], "aggregate": "mean", "days": 10, "requested_field": "close"}}
- "Cho tôi giá đóng nhỏ nhất của SSI từ đầu tháng"
  -> {{"tickers": ["SSI"], "aggregate": "min", "requested_field": "close"}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class AggregateExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=AggregateParams)

    def extract(self, query: str) -> Dict[str, Any]:
        system_msg = SystemMessage(
            content=_PROMPT.format(
                query=query,
                format_instructions=self._parser.get_format_instructions(),
            )
        )
        try:
            response = self._llm_provider.invoke_with_fallback([system_msg])
        except Exception as e:
            logger.warning("aggregate extractor LLM call failed: %s", e)
            return {"query_type": "aggregate_query", "tickers": [], "aggregate": "mean", "requested_field": "close"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("aggregate extractor parse failed: %s", e)
            return {"query_type": "aggregate_query", "tickers": [], "aggregate": "mean", "requested_field": "close"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: AggregateParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "aggregate_query",
            "tickers": p.tickers,
            "aggregate": p.aggregate,
            "requested_field": p.requested_field,
        }
        if p.days is not None:
            result["days"] = p.days
        if p.weeks is not None:
            result["weeks"] = p.weeks
        if p.months is not None:
            result["months"] = p.months
        return result
