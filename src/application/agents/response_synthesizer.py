import logging
import re

from langchain_core.messages import SystemMessage, HumanMessage
from infrastructure.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


def _get_synthesis_prompt() -> str:
    from application.prompts import PromptRegistryError, get_registry

    try:
        return get_registry().render("response_synthesis").text
    except PromptRegistryError:
        logger.exception("response_synthesis prompt render failed — using fallback")
        return (
            "Bạn là trợ lý tổng hợp dữ liệu chứng khoán. "
            "Tổng hợp các kết quả bên dưới thành câu trả lời mạch lạc bằng tiếng Việt, "
            "giữ nguyên số liệu và KHÔNG thêm thông tin mới."
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
                    SystemMessage(content=_get_synthesis_prompt()),
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
