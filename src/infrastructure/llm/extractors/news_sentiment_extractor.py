import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class NewsSentimentParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Stock ticker symbols, e.g. ['VCB']"
    )
    requested_field: str = Field(
        "news", description="Field: news, sentiment, social_volume, news_sentiment_score, social_sentiment_score, news_volume"
    )
    compare_with: Optional[List[str]] = Field(
        None, description="Optional tickers to compare sentiment with"
    )
    days: Optional[int] = Field(None, description="Number of days")
    weeks: Optional[int] = Field(None, description="Number of weeks")
    months: Optional[int] = Field(None, description="Number of months")


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi tin tức và tâm lý thị trường.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- requested_field: loại dữ liệu (news/sentiment/social_volume/...)
- compare_with: mã so sánh (mảng string, tùy chọn)
- days/weeks/months: khoảng thời gian

Ví dụ:
- "Tin tức về VCB trong tuần qua"
  -> {{"tickers": ["VCB"], "requested_field": "news", "weeks": 1}}
- "So sánh tâm lý thị trường giữa VIC và VHM 1 tháng gần đây"
  -> {{"tickers": ["VIC"], "compare_with": ["VHM"], "requested_field": "sentiment", "months": 1}}
- "Social volume của HPG hôm nay"
  -> {{"tickers": ["HPG"], "requested_field": "social_volume", "days": 1}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class NewsSentimentExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=NewsSentimentParams)

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
            logger.warning("news_sentiment extractor LLM call failed: %s", e)
            return {"query_type": "news_sentiment_query", "tickers": [], "requested_field": "news"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("news_sentiment extractor parse failed: %s", e)
            return {"query_type": "news_sentiment_query", "tickers": [], "requested_field": "news"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: NewsSentimentParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "news_sentiment_query",
            "tickers": p.tickers,
            "requested_field": p.requested_field,
        }
        if p.compare_with is not None:
            result["compare_with"] = p.compare_with
        if p.days is not None:
            result["days"] = p.days
        if p.weeks is not None:
            result["weeks"] = p.weeks
        if p.months is not None:
            result["months"] = p.months
        return result
