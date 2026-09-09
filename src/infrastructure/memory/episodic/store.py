"""Qdrant-backed episodic memory — semantic retrieval over past turns.

Uses its own collection (default ``finsight_episodic``) so the weekly
full-replace of ``finsight_knowledge`` never wipes conversation history.
All reads/writes are scoped by ``user_id``.
"""

from __future__ import annotations

import contextlib
from typing import Any

from infrastructure.observability import get_logger
from infrastructure.rag import vector_store as vs
from infrastructure.rag.embedder import Embedder

from .schemas import Episode

logger = get_logger("memory.episodic")

EPISODIC_COLLECTION = "finsight_episodic"


class EpisodicStore:
    """Semantic store for past conversation episodes."""

    def __init__(
        self,
        collection: str = EPISODIC_COLLECTION,
        embedder: Embedder | None = None,
        min_score: float = 0.5,
        top_k: int = 5,
    ):
        self.collection = collection
        self._embedder = embedder
        self.min_score = min_score
        self.top_k = top_k
        self._ensured = False

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder()
        return self._embedder

    def ensure(self) -> None:
        """Create the collection (with user_id/session_id indexes) if needed."""
        from qdrant_client.http.models import PayloadSchemaType

        vs.ensure_collection(self.collection, dim=self.embedder.dim)
        client = vs._client()
        for f in ("user_id", "session_id"):
            with contextlib.suppress(Exception):
                client.create_payload_index(
                    collection_name=self.collection,
                    field_name=f,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
        self._ensured = True

    def _ensure(self) -> None:
        if not self._ensured:
            self.ensure()

    def add_episode(
        self,
        user_id: str,
        text: str,
        session_id: str | None = None,
        importance: float = 0.5,
        episode_type: str = "interaction",
    ) -> str | None:
        """Embed + upsert one episode. Returns episode id or None on failure."""
        if not text or not text.strip():
            return None
        try:
            self._ensure()
            episode = Episode(
                text=text,
                user_id=user_id,
                session_id=session_id,
                importance=importance,
                episode_type=episode_type,
            )
            vector = self.embedder.embed([text])[0]
            vs.upsert_points(
                self.collection,
                [{"id": episode.id, "vector": vector, "payload": episode.to_payload()}],
            )
            return episode.id
        except Exception as e:
            logger.warning("episodic add failed: %s", e)
            return None

    def search_episodes(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> dict[str, Any]:
        """Semantic search scoped to one user. Returns {hits, context, count}."""
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        limit = top_k or self.top_k
        threshold = self.min_score if min_score is None else min_score
        try:
            vector = self.embedder.embed([query])[0]
        except Exception as e:
            logger.warning("episodic embed failed: %s", e)
            return {"hits": [], "context": "", "count": 0, "error": str(e)}
        try:
            self._ensure()
            client = vs._client()
            flt = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
            res = client.query_points(
                collection_name=self.collection,
                query=vector,
                query_filter=flt,
                limit=limit,
                with_payload=True,
            )
            hits = [
                {"id": getattr(p, "id", None), "score": getattr(p, "score", None), "payload": getattr(p, "payload", {})}
                for p in getattr(res, "points", res)
            ]
        except Exception as e:
            logger.warning("episodic search failed: %s", e)
            return {"hits": [], "context": "", "count": 0, "error": str(e)}

        filtered = [h for h in hits if (h.get("score") or 0) >= threshold]
        contexts = [
            f"[Past turn | score={h.get('score', 0):.3f}]\n{(h.get('payload', {}).get('text', '') or '')[:600]}"
            for h in filtered[:limit]
        ]
        return {
            "hits": filtered[:limit],
            "context": "\n\n---\n\n".join(contexts),
            "count": len(filtered),
        }

    def clear_user_episodes(self, user_id: str) -> int:
        """Delete all episodes of one user. Returns deleted count."""
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        try:
            self._ensure()
            client = vs._client()
            flt = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
            total = 0
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=self.collection,
                    scroll_filter=flt,
                    limit=100,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False,
                )
                ids = [p.id for p in points]
                if ids:
                    client.delete(collection_name=self.collection, points_selector=ids)
                    total += len(ids)
                if offset is None:
                    break
            return total
        except Exception as e:
            logger.warning("episodic clear failed: %s", e)
            return 0

    def count(self, user_id: str | None = None) -> int:
        """Count episodes, optionally scoped to one user."""
        try:
            self._ensure()
            client = vs._client()
            if user_id is None:
                info = vs.collection_info(self.collection)
                return int(info.get("points_count") or 0)
            from qdrant_client.http.models import FieldCondition, Filter, MatchValue

            flt = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
            res = client.count(collection_name=self.collection, count_filter=flt, exact=True)
            return int(getattr(res, "count", 0) or 0)
        except Exception as e:
            logger.warning("episodic count failed: %s", e)
            return 0


# Alias kept for readability at call sites.
EpisodicMemory = EpisodicStore
