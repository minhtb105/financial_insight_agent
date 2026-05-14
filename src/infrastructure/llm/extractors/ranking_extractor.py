import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class RankingParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="List of tickers to rank, at least 2 e.g. ['FPT', 'MWG', 'VNM']"
    )
    requested_field: str = Field(
        "close", description="Field: open, close, volume, high, low"
    )
    aggregate: str = Field(
        "max", description="Aggregate: max, min, mean, latest"
    )
    days: Optional[int] = Field(None, description="Number of days")
    weeks: Optional[int] = Field(None, description="Number of weeks")
    months: Optional[int] = Field(None, description="Number of months")


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi xếp hạng cổ phiếu.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách các mã cần xếp hạng (mảng string, tối thiểu 2 mã, bắt buộc)
- requested_field: chỉ số để xếp hạng (open/close/volume/high/low)
- aggregate: cách tổng hợp (max/min/mean/latest)
- days/weeks/months: khoảng thời gian

Ví dụ:
- "Trong các mã FPT, MWG và VNM, mã nào có giá đóng cửa cao nhất trong 2 tháng?"
  -> {{"tickers": ["FPT", "MWG", "VNM"], "requested_field": "close", "aggregate": "max", "months": 2}}
- "Xếp hạng khối lượng giao dịch của VIC, VCB, HPG 1 tuần qua"
  -> {{"tickers": ["VIC", "VCB", "HPG"], "requested_field": "volume", "aggregate": "max", "weeks": 1}}
- "Mã nào có giá mở cửa thấp nhất hôm nay: SSI, VND, HCM?"
  -> {{"tickers": ["SSI", "VND", "HCM"], "requested_field": "open", "aggregate": "min", "days": 1}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class RankingExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=RankingParams)

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
            logger.warning("ranking extractor LLM call failed: %s", e)
            return {"query_type": "ranking_query", "tickers": [], "requested_field": "close", "aggregate": "max"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("ranking extractor parse failed: %s", e)
            return {"query_type": "ranking_query", "tickers": [], "requested_field": "close", "aggregate": "max"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: RankingParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "ranking_query",
            "tickers": p.tickers,
            "requested_field": p.requested_field,
            "aggregate": p.aggregate,
        }
        if p.days is not None:
            result["days"] = p.days
        if p.weeks is not None:
            result["weeks"] = p.weeks
        if p.months is not None:
            result["months"] = p.months
        return result
