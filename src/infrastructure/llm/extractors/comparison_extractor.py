import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ComparisonParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Primary group of tickers, e.g. ['VIC']"
    )
    compare_with: List[str] = Field(
        ..., description="Reference group of tickers, e.g. ['HPG']"
    )
    requested_field: str = Field(
        "close", description="Metric: open, close, volume, high, low"
    )
    days: Optional[int] = Field(None, description="Number of days")
    weeks: Optional[int] = Field(None, description="Number of weeks")
    months: Optional[int] = Field(None, description="Number of months")


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi so sánh cổ phiếu.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: nhóm chính cần so sánh (mảng string, bắt buộc)
- compare_with: nhóm tham chiếu để so sánh (mảng string, bắt buộc)
- requested_field: chỉ số cần so sánh (open/close/volume/high/low)
- days/weeks/months: khoảng thời gian

Ví dụ:
- "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần"
  -> {{"tickers": ["VIC"], "compare_with": ["HPG"], "requested_field": "volume", "weeks": 1}}
- "So sánh giá đóng của VCB với BID hôm nay"
  -> {{"tickers": ["VCB"], "compare_with": ["BID"], "requested_field": "close", "days": 1}}
- "So sánh giá mở của TCB với MBB 5 ngày gần đây"
  -> {{"tickers": ["TCB"], "compare_with": ["MBB"], "requested_field": "open", "days": 5}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class ComparisonExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=ComparisonParams)

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
            logger.warning("comparison extractor LLM call failed: %s", e)
            return {"query_type": "comparison_query", "tickers": [], "compare_with": [], "requested_field": "close"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("comparison extractor parse failed: %s", e)
            return {"query_type": "comparison_query", "tickers": [], "compare_with": [], "requested_field": "close"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: ComparisonParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "comparison_query",
            "tickers": p.tickers,
            "compare_with": p.compare_with,
            "requested_field": p.requested_field,
        }
        if p.days is not None:
            result["days"] = p.days
        if p.weeks is not None:
            result["weeks"] = p.weeks
        if p.months is not None:
            result["months"] = p.months
        return result
