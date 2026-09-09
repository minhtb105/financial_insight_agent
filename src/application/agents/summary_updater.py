"""
SummaryUpdater — maintains per-user summary entities/topics after each turn.

Separate from QueryReformulator by design and never calls the LLM itself:
it reuses the entities/topics already extracted during rewriting, falling
back to known-ticker regex extraction when the LLM returned nothing.
"""

import logging
import re

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"\b[A-Z]{3,4}\b")


class SummaryUpdater:
    def update(
        self,
        user_id: str | None,
        entities: list[str] | None,
        topics: list[str] | None,
        raw_query: str = "",
        rewritten_query: str = "",
    ) -> dict:
        """Merge entities/topics into the user's summary state. Never raises."""
        try:
            from infrastructure.guardrails.tickers import VIETNAMESE_TICKERS
            from infrastructure.memory.memory_manager import get_memory_manager
        except Exception as e:
            logger.warning("SummaryUpdater unavailable: %s", e)
            return {"entities": [], "topics": [], "updated_at": None}

        merged_entities = list(entities or [])
        if not merged_entities:
            merged_entities = self._extract_tickers(raw_query, rewritten_query, VIETNAMESE_TICKERS)
        try:
            mgr = get_memory_manager()
            if mgr is None or mgr.short_term is None:
                return {"entities": merged_entities, "topics": list(topics or []), "updated_at": None}
            uid = mgr._validated_user_id(user_id)
            return mgr.short_term.update_summary(
                user_id=uid, entities=merged_entities, topics=list(topics or [])
            )
        except Exception as e:
            logger.warning("Summary update failed: %s", e)
            return {"entities": merged_entities, "topics": list(topics or []), "updated_at": None}

    @staticmethod
    def _extract_tickers(raw_query: str, rewritten_query: str, known: frozenset) -> list[str]:
        found = []
        for text in (rewritten_query, raw_query):
            for tok in _TICKER_RE.findall(text or ""):
                if tok in known and tok not in found:
                    found.append(tok)
        return found
