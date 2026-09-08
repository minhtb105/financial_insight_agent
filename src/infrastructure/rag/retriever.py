"""Retriever — search_knowledge for agent tool-calling."""

from __future__ import annotations

from typing import Any

from infrastructure.observability import get_logger
from .embedder import embed_query
from .vector_store import ALIAS, search as vs_search

logger = get_logger("rag.retriever")

_SAFETY_KEYWORDS = ["mua ngay", "bán ngay", "khuyến nghị mua", "khuyến nghị bán", "all-in"]


def _format_citation(payload: dict[str, Any], score: float) -> str:
    title = payload.get("title", payload.get("source_id", ""))
    url = payload.get("source_url", "")
    priority = payload.get("priority", 5)
    text = payload.get("text", "")[:600]
    return f"[Nguồn: {title} | priority={priority} | score={score:.3f} | {url}]\n{text}"


def search_knowledge(query: str, top_k: int = 5, min_score: float = 0.3) -> dict[str, Any]:
    """Search RAG knowledge base. Returns dict with hits and formatted context."""
    try:
        vec = embed_query(query)
    except Exception as e:
        logger.warning("retriever embed failed: %s", e)
        return {"hits": [], "context": "", "error": str(e)}

    try:
        hits = vs_search(ALIAS, vec, top_k=top_k)
    except Exception as e:
        logger.warning("retriever search failed (alias %s): %s", ALIAS, e)
        return {"hits": [], "context": "", "error": str(e)}

    # filter by score and rerank by priority (lower priority number = higher trust)
    filtered = [h for h in hits if (h.get("score") or 0) >= min_score]
    # sort by priority then score descending
    filtered.sort(key=lambda h: (h.get("payload", {}).get("priority", 99), - (h.get("score") or 0)))

    contexts = []
    for h in filtered[:top_k]:
        payload = h.get("payload", {})
        contexts.append(_format_citation(payload, h.get("score", 0)))

    return {
        "hits": [{"score": h.get("score"), "payload": h.get("payload")} for h in filtered[:top_k]],
        "context": "\n\n---\n\n".join(contexts),
        "count": len(filtered),
    }


def is_disallowed_advice(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _SAFETY_KEYWORDS)
