"""Qdrant vector store helpers — blue/green with alias finsight_knowledge."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PayloadSchemaType

ALIAS = "finsight_knowledge"
DEFAULT_DIM = 1536
BACKUP_KEEP_DAYS = 7


def _client() -> QdrantClient:
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    api_key = os.getenv("QDRANT_API_KEY")
    return QdrantClient(host=host, port=port, api_key=api_key, timeout=30)


def _week_label(dt: datetime | None = None) -> str:
    from infrastructure.rag.utils import week_label

    return week_label(dt)


def collection_name_for_week(week: str | None = None) -> str:
    lab = week or _week_label()
    return f"{ALIAS}_{lab}"


def ensure_collection(name: str, dim: int = DEFAULT_DIM, recreate: bool = False) -> None:
    c = _client()
    exists = c.collection_exists(name)
    if exists and recreate:
        c.delete_collection(name)
        exists = False
    if not exists:
        c.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        # payload indexes for filtering/rerank
        for field in ("priority", "source_id", "week"):
            try:
                c.create_payload_index(collection_name=name, field_name=field, field_schema=PayloadSchemaType.KEYWORD)
            except Exception:
                pass


def alias_target() -> str | None:
    c = _client()
    try:
        aliases = c.get_aliases()
        for a in aliases.aliases if hasattr(aliases, "aliases") else []:
            if getattr(a, "alias_name", None) == ALIAS:
                return getattr(a, "collection_name", None)
        # fallback: list collections and check alias via get_collection_aliases?
        # qdrant 1.11+ get_aliases returns dict
        if isinstance(aliases, dict):
            return aliases.get(ALIAS)
    except Exception:
        pass
    # last resort: if alias collection exists directly
    try:
        if c.collection_exists(ALIAS):
            return ALIAS
    except Exception:
        pass
    return None


def swap_alias(new_collection: str) -> None:
    c = _client()
    # create alias pointing to new_collection (atomic)
    # strategy: delete old alias then create new one using update_collection_aliases
    from qdrant_client.http.models import CreateAliasOperation, DeleteAliasOperation

    ops = []
    current = alias_target()
    if current:
        ops.append(DeleteAliasOperation(delete_alias={"alias_name": ALIAS}))
    ops.append(CreateAliasOperation(create_alias={"collection_name": new_collection, "alias_name": ALIAS}))
    try:
        c.update_collection_aliases(change_aliases_operations=ops)
    except Exception:
        # fallback: simple create
        try:
            c.create_alias(alias_name=ALIAS, collection_name=new_collection)
        except Exception:
            pass


def upsert_points(collection: str, points: list[dict[str, Any]], batch_size: int = 100) -> int:
    c = _client()
    total = 0
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        # qdrant expects id, vector, payload
        c.upsert(collection_name=collection, points=batch)  # type: ignore
        total += len(batch)
    return total


def search(collection_or_alias: str, vector: list[float], top_k: int = 5, filter_priority: int | None = None) -> list[dict[str, Any]]:
    c = _client()
    flt = None
    if filter_priority is not None:
        from qdrant_client.http.models import Filter, FieldCondition, Range
        flt = Filter(must=[FieldCondition(key="priority", range=Range(gte=None, lte=filter_priority))])
    res = c.query_points(collection_name=collection_or_alias, query=vector, limit=top_k, query_filter=flt, with_payload=True)
    out = []
    for p in getattr(res, "points", res):
        out.append({"id": getattr(p, "id", None), "score": getattr(p, "score", None), "payload": getattr(p, "payload", {})})
    return out


def list_collections() -> list[str]:
    c = _client()
    cols = c.get_collections()
    return [col.name for col in cols.collections]


def cleanup_old_backups(keep_days: int = BACKUP_KEEP_DAYS) -> list[str]:
    """Delete collections older than keep_days, keep alias target."""
    c = _client()
    target = alias_target()
    # Parse collection names finsight_knowledge_YYYYwWW
    to_delete = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    for name in list_collections():
        if not name.startswith(ALIAS + "_"):
            continue
        if name == target:
            continue
        # try parse week label -> approx date (Monday of that week)
        try:
            lab = name[len(ALIAS) + 1 :]  # YYYYwWW
            year = int(lab[:4])
            week = int(lab[5:7])
            # approximate monday
            d = datetime.strptime(f"{year}-{week}-1", "%Y-%W-%w").replace(tzinfo=timezone.utc)
            if d < cutoff:
                to_delete.append(name)
        except Exception:
            # if unparseable, not deleting
            continue
    for n in to_delete:
        try:
            c.delete_collection(n)
        except Exception:
            pass
    return to_delete


def collection_info(name: str) -> dict[str, Any]:
    c = _client()
    try:
        info = c.get_collection(name)
        return {"name": name, "points_count": getattr(info, "points_count", None), "vectors_count": getattr(info, "vectors_count", None)}
    except Exception as e:
        return {"name": name, "error": str(e)}
