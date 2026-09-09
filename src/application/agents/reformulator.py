"""
QueryReformulator — rewrites context-dependent follow-up questions into
self-contained questions before query splitting.

Single-turn (q_{t-1}, r_{t-1}, q_t) design adapted from FollowGPT (CIKM'25
§3.1/§3.3): rewrite each raw question once using the previous turn, then
let downstream splitting operate on the resolved text. No history → no LLM
call. Any failure → return the raw query unchanged.
"""

import logging
import threading
import time
from collections import OrderedDict
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from infrastructure.llm.llm_provider import LLMProvider, ReformulatedQuery

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_DELAY = 1.0
_CACHE_TTL = 3600  # 1 hour
_CACHE_MAX = 512
_cache: OrderedDict[tuple[str, str, str], tuple[float, tuple[str, list[str], list[str]]]] = OrderedDict()
_cache_lock = threading.Lock()

_FALLBACK_PROMPT = (
    "Bạn là bộ viết lại câu hỏi tài chính. Viết lại CÂU HỎI HIỆN TẠI thành câu "
    "ĐỘC LẬP, đầy đủ nghĩa mà không cần hội thoại trước đó. Giữ nguyên ý định, "
    "bổ sung chi tiết còn thiếu từ hội thoại, không thêm thông tin mới. "
    "Nếu câu hỏi đã độc lập hoặc không liên quan tới hội thoại, trả nguyên văn. "
    "Output phải là JSON hợp lệ theo schema."
)


def _cache_get(key: tuple[str, str, str]) -> tuple[str, list[str], list[str]] | None:
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if not hit:
            return None
        ts, value = hit
        if now - ts < _CACHE_TTL:
            _cache.move_to_end(key)
            return value
        del _cache[key]
        return None


def _cache_put(key: tuple[str, str, str], value: tuple[str, list[str], list[str]]) -> None:
    with _cache_lock:
        _cache[key] = (time.time(), value)
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


class QueryReformulator:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider
        self.llm = self.llm_provider.with_structured_output(
            pydantic_object=ReformulatedQuery,
            method="json_schema",
            fallback=True,
        )

    # ------------------------------------------------------------------
    # Prompt input
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt_input(raw_query: str, mem_inputs: dict[str, Any]) -> dict[str, str]:
        working = mem_inputs.get("working") or {}
        sliding = mem_inputs.get("sliding") or {}
        episodic = mem_inputs.get("episodic") or {}
        turns = sliding.get("turns") or []
        recent = []
        for t in turns[-2:]:
            if isinstance(t, dict):
                recent.append(f"Hỏi: {t.get('user_query', '')} / Đáp: {t.get('agent_response', '')[:300]}")
        return {
            "query": raw_query,
            "prev_q": working.get("previous_user_query", ""),
            "prev_r": (working.get("previous_system_response", "") or "")[:800],
            "sliding": "\n".join(recent),
            "episodic": (episodic.get("context", "") or "")[:600],
        }

    @staticmethod
    def _has_history(mem_inputs: dict[str, Any]) -> bool:
        working = mem_inputs.get("working") or {}
        sliding = mem_inputs.get("sliding") or {}
        episodic = mem_inputs.get("episodic") or {}
        return bool(
            working.get("turn_id")
            or working.get("previous_user_query")
            or sliding.get("turns")
            or episodic.get("hits")
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rewrite(
        self,
        raw_query: str,
        mem_inputs: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> tuple[str, list[str], list[str]]:
        """Return (rewritten, entities, topics). Falls back to raw query."""
        if not raw_query or not raw_query.strip():
            return raw_query, [], []
        mem_inputs = mem_inputs or {}
        if not self._has_history(mem_inputs):
            return raw_query, [], []

        working = mem_inputs.get("working") or {}
        key = (user_id or "anonymous", raw_query.strip(), str(working.get("turn_id")))
        cached = _cache_get(key)
        if cached:
            return cached

        result = self._llm_rewrite(raw_query, mem_inputs)
        _cache_put(key, result)
        return result

    # ------------------------------------------------------------------
    # LLM rewrite
    # ------------------------------------------------------------------

    def _llm_rewrite(
        self, raw_query: str, mem_inputs: dict[str, Any]
    ) -> tuple[str, list[str], list[str]]:
        from application.prompts import PromptRegistryError, get_registry

        variables = self._build_prompt_input(raw_query, mem_inputs)
        try:
            system_prompt = get_registry().render("query_reformulation", **variables).text
        except PromptRegistryError:
            logger.exception("query_reformulation prompt render failed — using fallback")
            system_prompt = _FALLBACK_PROMPT

        for attempt in range(1 + _MAX_RETRIES):
            try:
                resp = self.llm.invoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=raw_query),
                    ],
                    timeout=30,
                )
                if resp and getattr(resp, "rewritten", ""):
                    entities = list(getattr(resp, "entities", None) or [])
                    topics = list(getattr(resp, "topics", None) or [])
                    return resp.rewritten, entities, topics
                logger.warning("Empty rewrite response — keeping raw query")
                return raw_query, [], []
            except Exception as e:
                logger.warning("LLM rewrite attempt %d/%d failed: %s", attempt + 1, 1 + _MAX_RETRIES, e)
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY)

        logger.exception("LLM rewrite failed after %d retries", _MAX_RETRIES)
        return raw_query, [], []
