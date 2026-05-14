import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ForecastParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Stock ticker symbols, e.g. ['VCB']"
    )
    timeframe: str = Field(
        "1w", description="Forecast timeframe: 1d, 1w, 1M, 3M"
    )
    model: Optional[str] = Field(
        None, description="Forecast model (optional)"
    )


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi dự báo cổ phiếu.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- timeframe: khung thời gian dự báo (1d/1w/1M/3M, mặc định 1w)
- model: mô hình dự báo (string, tùy chọn)

Ví dụ:
- "Dự báo giá VCB tuần tới"
  -> {{"tickers": ["VCB"], "timeframe": "1w"}}
- "Dự đoán xu hướng HPG 3 tháng tới"
  -> {{"tickers": ["HPG"], "timeframe": "3M"}}
- "Forecast VIC theo mô hình SMA"
  -> {{"tickers": ["VIC"], "timeframe": "1w", "model": "sma"}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class ForecastExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=ForecastParams)

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
            logger.warning("forecast extractor LLM call failed: %s", e)
            return {"query_type": "forecast_query", "tickers": [], "timeframe": "1w"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("forecast extractor parse failed: %s", e)
            return {"query_type": "forecast_query", "tickers": [], "timeframe": "1w"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: ForecastParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "forecast_query",
            "tickers": p.tickers,
            "timeframe": p.timeframe,
        }
        if p.model is not None:
            result["model"] = p.model
        return result
