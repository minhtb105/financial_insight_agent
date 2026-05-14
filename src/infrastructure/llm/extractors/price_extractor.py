import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class PriceParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Stock ticker symbols, e.g. ['VCB']"
    )
    requested_field: str = Field(
        "close", description="Field: open, close, volume, ohlcv, high, low"
    )
    days: Optional[int] = Field(None, description="Number of days")
    weeks: Optional[int] = Field(None, description="Number of weeks")
    months: Optional[int] = Field(None, description="Number of months")


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi dữ liệu giá chứng khoán.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- requested_field: trường dữ liệu (open/close/volume/ohlcv/high/low)
- days/weeks/months: khoảng thời gian

Ví dụ:
- "Lấy giá mở cửa của VCB hôm qua"
  -> {{"tickers": ["VCB"], "requested_field": "open", "days": 1}}
- "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất"
  -> {{"tickers": ["HPG"], "requested_field": "ohlcv", "days": 10}}
- "Giá mở cửa của VIC trong 5 ngày vừa rồi"
  -> {{"tickers": ["VIC"], "requested_field": "open", "days": 5}}
- "Lấy giá đóng cửa của HPG hôm nay"
  -> {{"tickers": ["HPG"], "requested_field": "close", "days": 1}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class PriceExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=PriceParams)

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
            logger.warning("price extractor LLM call failed: %s", e)
            return {"query_type": "price_query", "tickers": [], "requested_field": "close"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("price extractor parse failed: %s", e)
            return {"query_type": "price_query", "tickers": [], "requested_field": "close"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: PriceParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "price_query",
            "tickers": p.tickers,
            "requested_field": p.requested_field,
        }
        if p.days is not None:
            result["days"] = p.days
        if p.weeks is not None:
            result["weeks"] = p.weeks
        if p.months is not None:
            result["months"] = p.months
        return result
