import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class SectorParams(BaseModel):
    sector: str = Field(
        ..., description="Sector name, e.g. banking, real estate, retail"
    )
    metric: str = Field(
        "performance", description="Metric: performance, volume"
    )
    timeframe: str = Field(
        "1w", description="Timeframe: 1d, 1w, 1M"
    )


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi phân tích ngành.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- sector: tên ngành (string, bắt buộc) - banking, real estate, retail, ...
- metric: chỉ số (performance/volume, mặc định performance)
- timeframe: khung thời gian (1d/1w/1M, mặc định 1w)

Ví dụ:
- "Hiệu suất ngành ngân hàng tuần này thế nào?"
  -> {{"sector": "banking", "metric": "performance", "timeframe": "1w"}}
- "Khối lượng giao dịch ngành bất động sản hôm nay"
  -> {{"sector": "real estate", "metric": "volume", "timeframe": "1d"}}
- "Phân tích ngành bán lẻ 1 tháng qua"
  -> {{"sector": "retail", "metric": "performance", "timeframe": "1M"}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class SectorExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=SectorParams)

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
            logger.warning("sector extractor LLM call failed: %s", e)
            return {"query_type": "sector_query", "sector": "", "metric": "performance", "timeframe": "1w"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("sector extractor parse failed: %s", e)
            return {"query_type": "sector_query", "sector": "", "metric": "performance", "timeframe": "1w"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: SectorParams) -> Dict[str, Any]:
        return {
            "query_type": "sector_query",
            "sector": p.sector,
            "metric": p.metric,
            "timeframe": p.timeframe,
        }
