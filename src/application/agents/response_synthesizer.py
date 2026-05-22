import logging
import re

from langchain_core.messages import SystemMessage, HumanMessage
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

_SYNTHESIS_PROMPT = (
    "Bạn là trợ lý tổng hợp dữ liệu chứng khoán.\n"
    "Nhiệm vụ: Tổng hợp các kết quả phân tích bên dưới thành "
    "câu trả lời MẠCH LẠC bằng tiếng Việt.\n"
    "- Giữ nguyên số liệu cụ thể\n"
    "- Loại bỏ trùng lặp\n"
    "- Sắp xếp thứ tự hợp lý\n"
    "- Nếu có dữ liệu không liên quan, bỏ qua\n"
    "- KHÔNG thêm thông tin không có trong kết quả"
)


class ResponseSynthesizer:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm_provider = llm_provider

    @staticmethod
    def _strip_error_prefix(answer: str) -> str:
        return re.sub(r"^TOOL_ERR#.*?\n?", "", answer.strip())

    def synthesize(self, answers: list[str], query: str) -> str:
        if len(answers) <= 1:
            return self._strip_error_prefix(answers[0]) if answers else ""

        stripped = [self._strip_error_prefix(a) for a in answers if self._strip_error_prefix(a)]
        combined = "\n\n".join(stripped)

        try:
            resp = self._llm_provider.invoke_with_fallback(
                [
                    SystemMessage(content=_SYNTHESIS_PROMPT),
                    HumanMessage(
                        content=f"Câu hỏi gốc: {query}\n\nKết quả:\n{combined}"
                    ),
                ]
            )
            return resp.content if hasattr(resp, "content") else combined
        except Exception:
            logger.warning("Synthesis LLM failed, falling back to concatenation")
            return self._deduplicate_concat(answers)

    @staticmethod
    def _deduplicate_concat(answers: list[str]) -> str:
        seen = set()
        deduped = []
        for a in answers:
            key = re.sub(r"\s+", " ", a.strip())[:300]
            if key not in seen:
                seen.add(key)
                deduped.append(a)
        return "\n\n".join(deduped) if deduped else "\n\n".join(answers)
