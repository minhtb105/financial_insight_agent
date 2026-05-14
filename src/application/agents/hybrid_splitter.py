import logging
import re
from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from infrastructure.llm.llm_provider import LLMProvider, MultiQuery

logger = logging.getLogger(__name__)


class HybridQuerySplitter:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or LLMProvider()
        self.llm = self.llm_provider.with_structured_output(
            pydantic_object=MultiQuery,
            method="json_schema",
            fallback=True,
        )

    # ----------------------------------------------------------------------
    # RULE-BASED SPLIT
    # ----------------------------------------------------------------------
    def _rule_split(self, text: str) -> List[str]:
        """
        Tách nhanh các case phổ biến bằng rule.
        Nếu text phù hợp rule → trả về list câu tách.
        Nếu không phù hợp → trả về [] để LLM xử lý.
        """
        if not text:
            return []

        original = text.lower()

        # 1) Split by "."
        if "." in text:
            parts = [p.strip() for p in text.split(".") if p.strip()]
            if len(parts) > 1:
                return parts

        # Ex: "Tính SMA9 và SMA20 của VIC"
        if " và " in original:
            # 2 intent but the same indicator -> remain unchanged
            if re.search(r"(sma|rsi|macd|giá|volume|ohlcv)", original):
                # Ex: "SMA9 và SMA20"
                if re.search(r"sma\s*\d+\s* và\s* sma?\s*\d+", original):
                    return []

            # Split when 2 actions appear
            action_words = ["lấy", "tính", "so sánh", "xem", "phân tích"]
            count = sum(1 for w in action_words if w in original)

            if count >= 2:
                # Split by "và"
                parts = [p.strip() for p in text.split(" và ") if p.strip()]
                if len(parts) > 1:
                    return parts

        # 3) Pattern "..., rồi ..."
        if " rồi " in original:
            parts = [p.strip() for p in re.split(
                r"\broi?[̀]?\b|\brồi\b", text) if p.strip()]
            if len(parts) > 1:
                return parts

        return []

    # ----------------------------------------------------------------------
    # LLM FALLBACK
    # ----------------------------------------------------------------------
    def _llm_split(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []

        system_prompt = (
            "Bạn là bộ tách câu hỏi tài chính.\n"
            "Nhiệm vụ: tách câu đầu vào thành danh sách các câu hỏi độc lập.\n"
            "- Không được tự tạo câu hỏi mới\n"
            "- Không được viết giải thích\n"
            "- Output phải là JSON hợp lệ theo schema"
        )

        try:
            resp = self.llm.invoke([
                SystemMessage(system_prompt),
                HumanMessage(text),
            ])
            return resp.queries if resp and hasattr(resp, "queries") else []
        except Exception:
            logger.exception("LLM split failed")
            return []

    # ----------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------
    def split(self, text: str) -> List[str]:
        """
        Return list of questions answered by hybrid approach.
        """
        if not text or not text.strip():
            return []

        # 1) Try rule first
        rule_result = self._rule_split(text)
        if rule_result:
            return rule_result

        # 2) Fallback LLM
        return self._llm_split(text)
