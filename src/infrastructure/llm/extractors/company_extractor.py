import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from . import BaseExtractor
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class CompanyParams(BaseModel):
    tickers: List[str] = Field(
        ..., description="Stock ticker symbols, e.g. ['VNM']"
    )
    requested_field: str = Field(
        "shareholders", description="Field: shareholders, executives, subsidiaries"
    )


_PROMPT = """
Bạn là chuyên gia trích xuất tham số cho câu hỏi thông tin công ty.

Từ câu hỏi, hãy trích xuất các thông tin sau:
- tickers: danh sách mã cổ phiếu (mảng string, bắt buộc)
- requested_field: loại thông tin (shareholders/executives/subsidiaries)

Ví dụ:
- "Cổ đông lớn nhất của VNM là ai?"
  -> {{"tickers": ["VNM"], "requested_field": "shareholders"}}
- "Cho tôi thông tin ban lãnh đạo của HPG"
  -> {{"tickers": ["HPG"], "requested_field": "executives"}}
- "Công ty con của VIC gồm những ai?"
  -> {{"tickers": ["VIC"], "requested_field": "subsidiaries"}}

Chỉ trả về JSON, không giải thích thêm.
{format_instructions}

Câu hỏi: {query}
"""


class CompanyExtractor(BaseExtractor):
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._parser = PydanticOutputParser(pydantic_object=CompanyParams)

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
            logger.warning("company extractor LLM call failed: %s", e)
            return {"query_type": "company_query", "tickers": [], "requested_field": "shareholders"}

        try:
            parsed = self._parser.parse(response.content)
        except Exception as e:
            logger.warning("company extractor parse failed: %s", e)
            return {"query_type": "company_query", "tickers": [], "requested_field": "shareholders"}

        return self._to_dict(parsed)

    @staticmethod
    def _to_dict(p: CompanyParams) -> Dict[str, Any]:
        return {
            "query_type": "company_query",
            "tickers": p.tickers,
            "requested_field": p.requested_field,
        }
