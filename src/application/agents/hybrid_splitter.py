"""
HybridQuerySplitter — splits compound Vietnamese stock queries into independent sub-queries.

Uses rule-based splitting first (fast, no LLM), then falls back to LLM
for ambiguous multi-intent sentences. Used by the agent BEFORE the ReAct loop
so each sub-query goes through a clean tool-calling cycle.
"""

import logging
import re
import time
import threading
from collections import OrderedDict

from langchain_core.messages import SystemMessage, HumanMessage

from infrastructure.llm.llm_provider import LLMProvider, MultiQuery

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2

_ACTION_WORDS = ["lấy", "tính", "so sánh", "xem", "phân tích", "kiểm tra", "dự báo"]
_RETRY_DELAY = 1.0
_LLM_SPLIT_CACHE_TTL = 3600  # 1 hour
_LLM_SPLIT_CACHE_MAX = 512
_llm_split_cache: OrderedDict[str, tuple[float, list[str]]] = OrderedDict()
_llm_split_cache_lock = threading.Lock()


class HybridQuerySplitter:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider
        self.llm = self.llm_provider.with_structured_output(
            pydantic_object=MultiQuery,
            method="json_schema",
            fallback=True,
        )

    # ------------------------------------------------------------------
    # Rule-based split (fast path)
    # ------------------------------------------------------------------

    def _rule_split(self, text: str) -> list[str]:
        """
        Quickly split common patterns without hitting the LLM.
        Returns [] when no rule matches (→ falls through to LLM).
        """
        if not text:
            return []

        original = text.lower()

        # 1) Split by sentence boundary (period + space)
        # Exclude Vietnamese abbreviations: Tp.HCM, ticker.Exchange (VCB.HNX),
        # decimal numbers (12.5%), and common abbreviations (e.g., etc.)
        _KNOWN_ABBREV = re.compile(
            r"(?:Tp|tp|Thành phố|TP)\.[A-Z]|"         # Tp.HCM
            r"[A-Z]{2,4}\.(HNX|HOSE|UPCOM)|"           # VCB.HNX
            r"\d+\.\d+%?|"                              # 12.5 or 12.5%
            r"[A-Z]\.\s*[A-Z]\.",                       # N.N. (initials)
            re.IGNORECASE,
        )
        if re.search(r'(?<![A-Za-z0-9])[.!?](?:\s|$)', text):
            sentences = re.split(r"(?<=[.!?])\s+|(?<=[.!?])[\n\r]+", text)
            if len(sentences) > 1:
                valid = [s.strip() for s in sentences if s.strip()]
                # Don't split if any sentence boundary matches known abbreviation
                if len(valid) > 1 and not _KNOWN_ABBREV.search(text):
                    return valid

        # 2) "và" connector: only split when ≥2 distinct action verbs appear
        if re.search(r"\bvà\b", original):
            # Comparative patterns: "tính P/E của VCB và so sánh với HPG"
            # should stay as one single comparison query, not split.
            if re.search(r"và\s+(so\s+sánh|so\s+với)", original):
                return []
            # Same-action patterns: keep as one query
            #   "SMA9 và SMA20 của VIC" / "P/E và P/B của VCB"
            #   "lấy giá đóng cửa và khối lượng của VCB"
            if re.search(r"(sma|ma|rsi|macd|pe|pb|roe|eps|giá|khối lượng|volume|close|open)\s*\d*\s*và\s*(sma|ma|rsi|macd|pe|pb|roe|eps|giá|khối lượng|volume|close|open)", original):
                return []

            count = sum(1 for w in _ACTION_WORDS if w in original)

            if count >= 2:
                parts = [
                    p.strip() for p in re.split(r"\bvà\b", text, flags=re.IGNORECASE) if p.strip()
                ]
                if len(parts) > 1:
                    # Check if same action word appears in all parts → single intent
                    first_action = next((w for w in _ACTION_WORDS if w in parts[0].lower()), None)
                    if first_action:
                        other_actions = [next((w for w in _ACTION_WORDS if w in p.lower()), None) for p in parts[1:]]
                        if all(a == first_action for a in other_actions):
                            return []
                    return parts

        # 3) "rồi" sequential pattern
        if re.search(r"\brồi\b", original):
            parts = [
                p.strip() for p in re.split(r"\brồi\b", text, flags=re.IGNORECASE) if p.strip()
            ]
            if len(parts) > 1:
                return parts

        # 4) Comma-separated clauses with action words
        if ", " in text:
            parts = [p.strip() for p in text.split(", ") if p.strip()]
            if len(parts) > 1:
                multi_action = sum(1 for p in parts if any(w in p.lower() for w in _ACTION_WORDS))
                if multi_action >= 2:
                    return parts

        return []

    # ------------------------------------------------------------------
    # LLM fallback split
    # ------------------------------------------------------------------

    def _llm_split(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        now = time.time()
        with _llm_split_cache_lock:
            cached = _llm_split_cache.get(text)
            if cached:
                ts, result = cached
                if now - ts < _LLM_SPLIT_CACHE_TTL:
                    _llm_split_cache.move_to_end(text)
                    return result
                del _llm_split_cache[text]

        from application.prompts import PromptRegistryError, get_registry

        try:
            system_prompt = get_registry().render("query_splitter").text
        except PromptRegistryError:
            logger.exception("query_splitter prompt render failed — using fallback")
            system_prompt = (
                "Bạn là bộ tách câu hỏi tài chính. Tách câu đầu vào thành danh sách "
                "các câu hỏi ĐỘC LẬP nếu có nhiều ý định; nếu chỉ có 1 ý định, trả về "
                "danh sách chứa đúng 1 phần tử. Output phải là JSON hợp lệ theo schema."
            )

        for attempt in range(1 + _MAX_RETRIES):
            try:
                resp = self.llm.invoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=text),
                    ],
                    timeout=30,
                )
                result = (
                    resp.queries if resp and hasattr(resp, "queries") and resp.queries else [text]
                )
                with _llm_split_cache_lock:
                    _llm_split_cache[text] = (time.time(), result)
                    _llm_split_cache.move_to_end(text)
                    while len(_llm_split_cache) > _LLM_SPLIT_CACHE_MAX:
                        _llm_split_cache.popitem(last=False)
                return result
            except Exception as e:
                logger.warning(
                    "LLM split attempt %d/%d failed: %s", attempt + 1, 1 + _MAX_RETRIES, e
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY)

        logger.exception("LLM split failed after %d retries", _MAX_RETRIES)
        return [text]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def split(self, text: str) -> list[str]:
        """
        Return list of independent sub-queries.
        Single-intent queries return a list with exactly one element.
        """
        if not text or not text.strip():
            return []

        # 1) Try rule-based first (no LLM cost)
        rule_result = self._rule_split(text)
        if rule_result:
            logger.debug("Rule split → %d parts", len(rule_result))
            return rule_result

        # 2) Fallback to LLM
        llm_result = self._llm_split(text)
        logger.debug("LLM split → %d parts", len(llm_result))
        return llm_result
