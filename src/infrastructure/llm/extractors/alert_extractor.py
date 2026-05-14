import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class AlertParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Stock ticker symbols, e.g. ['VCB']"
    )
    threshold: float = Field(
        ..., description="Price threshold value"
    )
    condition: str = Field(
        "above", description="Condition: above, below"
    )
    timeframe: str = Field(
        "1d", description="Timeframe: 1d, 1w, 1h"
    )


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi cảnh báo chứng khoán.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- threshold: ngưỡng giá (số thực, bắt buộc)
- condition: điều kiện (above/below, mặc định above)
- timeframe: khung thời gian (1d/1w/1h, mặc định 1d)

Ví dụ:
- "Cảnh báo khi VCB vượt 80.000"
  -> {{"tickers": ["VCB"], "threshold": 80000, "condition": "above", "timeframe": "1d"}}
- "Báo cho tôi nếu HPG xuống dưới 25.000"
  -> {{"tickers": ["HPG"], "threshold": 25000, "condition": "below", "timeframe": "1d"}}
- "Cảnh báo khối lượng VIC vượt 5 triệu trong 1 giờ"
  -> {{"tickers": ["VIC"], "threshold": 5000000, "condition": "above", "timeframe": "1h"}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class AlertExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=AlertParams)

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
            logger.warning("alert extractor LLM call failed: %s", e)
            return {"query_type": "alert_query", "tickers": [], "threshold": 0, "condition": "above", "timeframe": "1d"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("alert extractor parse failed: %s", e)
            return {"query_type": "alert_query", "tickers": [], "threshold": 0, "condition": "above", "timeframe": "1d"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: AlertParams) -> Dict[str, Any]:
        return {
            "query_type": "alert_query",
            "tickers": p.tickers,
            "threshold": p.threshold,
            "condition": p.condition,
            "timeframe": p.timeframe,
        }
