import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class IndicatorParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Stock ticker symbols, e.g. ['VCB']"
    )
    indicator_type: str = Field(
        ..., description="Indicator: sma, rsi, macd, bb, stochastic, adx, atr, obv, cci"
    )
    indicator_period: Optional[int] = Field(
        None, description="Period for indicator, e.g. 9 for SMA9, 14 for RSI14"
    )
    days: Optional[int] = Field(None, description="Number of days")
    weeks: Optional[int] = Field(None, description="Number of weeks")
    months: Optional[int] = Field(None, description="Number of months")


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi chỉ báo kỹ thuật chứng khoán.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- indicator_type: loại chỉ báo (sma/rsi/macd/bb/stochastic/adx/atr/obv/cci)
- indicator_period: chu kỳ chỉ báo (số nguyên, ví dụ: SMA9 -> 9, RSI14 -> 14)
- days/weeks/months: khoảng thời gian

Ví dụ:
- "Tính SMA9 cho VCB trong 1 tuần gần nhất"
  -> {{"tickers": ["VCB"], "indicator_type": "sma", "indicator_period": 9, "weeks": 1}}
- "RSI14 của VIC từ đầu tháng 10 đến nay"
  -> {{"tickers": ["VIC"], "indicator_type": "rsi", "indicator_period": 14, "months": 1}}
- "Cho tôi SMA20 của HPG trong 2 tuần gần đây"
  -> {{"tickers": ["HPG"], "indicator_type": "sma", "indicator_period": 20, "weeks": 2}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class IndicatorExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=IndicatorParams)

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
            logger.warning("indicator extractor LLM call failed: %s", e)
            return {"query_type": "indicator_query", "tickers": [], "indicator_type": "sma", "requested_field": "sma", "indicator_params": {}}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("indicator extractor parse failed: %s", e)
            return {"query_type": "indicator_query", "tickers": [], "indicator_type": "sma", "requested_field": "sma", "indicator_params": {}}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: IndicatorParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "indicator_query",
            "tickers": p.tickers,
            "indicator_type": p.indicator_type,
            "requested_field": p.indicator_type,
            "indicator_params": {},
        }
        if p.indicator_period is not None:
            result["indicator_params"][p.indicator_type] = [p.indicator_period]
        if p.days is not None:
            result["days"] = p.days
        if p.weeks is not None:
            result["weeks"] = p.weeks
        if p.months is not None:
            result["months"] = p.months
        return result