import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class PortfolioParams(BaseModel):
    requested_field: str = Field(
        "portfolio_value", description="Field: portfolio_value, portfolio_performance, portfolio_allocation, portfolio_summary, performance, sector_allocation, portfolio_risk, portfolio_diversification, portfolio_turnover"
    )
    portfolio: Optional[Dict[str, int]] = Field(
        None, description="Holdings dict e.g. {'VCB': 1000, 'HPG': 500}"
    )
    tickers: Optional[List[str]] = Field(
        None, description="Optional ticker filter"
    )


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi danh mục đầu tư.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- requested_field: loại thông tin danh mục (portfolio_value/portfolio_performance/portfolio_allocation/...)
- portfolio: danh sách cổ phiếu kèm số lượng (dict, tùy chọn) {{"TICKER": số_lượng}}
- tickers: lọc theo mã (mảng string, tùy chọn)

Ví dụ:
- "Giá trị danh mục của tôi là bao nhiêu?"
  -> {{"requested_field": "portfolio_value"}}
- "Hiệu suất danh mục VCB 1000, HPG 500 trong tuần qua"
  -> {{"requested_field": "portfolio_performance", "portfolio": {{"VCB": 1000, "HPG": 500}}}}
- "Phân bổ ngành của danh mục tôi"
  -> {{"requested_field": "sector_allocation"}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class PortfolioExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=PortfolioParams)

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
            logger.warning("portfolio extractor LLM call failed: %s", e)
            return {"query_type": "portfolio_query", "requested_field": "portfolio_value"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("portfolio extractor parse failed: %s", e)
            return {"query_type": "portfolio_query", "requested_field": "portfolio_value"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: PortfolioParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "portfolio_query",
            "requested_field": p.requested_field,
        }
        if p.portfolio is not None:
            result["portfolio"] = p.portfolio
        if p.tickers is not None:
            result["tickers"] = p.tickers
        return result
