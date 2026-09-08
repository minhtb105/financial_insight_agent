"""Knowledge adapter implementing KnowledgePort via Qdrant."""

from __future__ import annotations

from typing import Any

from shared.ports.knowledge_port import KnowledgePort


class QdrantKnowledgeAdapter(KnowledgePort):
    def search(self, query: str, top_k: int = 5, min_score: float = 0.3) -> dict[str, Any]:
        from infrastructure.rag.retriever import search_knowledge

        return search_knowledge(query, top_k=top_k, min_score=min_score)
