import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class FinancialRatioParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Stock ticker symbols, e.g. ['VCB']"
    )
    requested_field: str = Field(
        "pe", description="Ratio: pe, pb, roe, eps, roa, debt_to_equity, current_ratio, quick_ratio, dividend_yield, operating_margin, net_margin, revenue_growth, eps_growth"
    )
    period: Optional[str] = Field(None, description="Period: quarter, year")
    quarter: Optional[int] = Field(None, description="Quarter number 1-4")
    year: Optional[int] = Field(None, description="Year")


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi tỷ lệ tài chính.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- requested_field: loại chỉ số (pe/pb/roe/eps/roa/debt_to_equity/dividend_yield/...)
- period: kỳ báo cáo (quarter hoặc year, tùy chọn)
- quarter: quý (1-4, tùy chọn)
- year: năm (tùy chọn)

Ví dụ:
- "PE của VCB hiện tại là bao nhiêu?"
  -> {{"tickers": ["VCB"], "requested_field": "pe"}}
- "ROE và EPS của HPG trong quý 1 năm 2024"
  -> {{"tickers": ["HPG"], "requested_field": "roe", "period": "quarter", "quarter": 1, "year": 2024}}
- "Chỉ số tài chính của FPT năm 2023"
  -> {{"tickers": ["FPT"], "requested_field": "financial_ratio", "period": "year", "year": 2023}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class FinancialRatioExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=FinancialRatioParams)

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
            logger.warning("financial_ratio extractor LLM call failed: %s", e)
            return {"query_type": "financial_ratio_query", "tickers": [], "requested_field": "pe"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("financial_ratio extractor parse failed: %s", e)
            return {"query_type": "financial_ratio_query", "tickers": [], "requested_field": "pe"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: FinancialRatioParams) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "query_type": "financial_ratio_query",
            "tickers": p.tickers,
            "requested_field": p.requested_field,
        }
        if p.period is not None:
            result["period"] = p.period
        if p.quarter is not None:
            result["quarter"] = p.quarter
        if p.year is not None:
            result["year"] = p.year
        return result
