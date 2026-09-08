"""Weekly full replace pipeline — fetch → chunk → embed → Qdrant blue/green."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from infrastructure.observability import get_logger
from .embedder import Embedder
from .ingestion.connectors import ingest_source
from .processing.chunker import chunk_text, dedupe_chunks
from .registry import add_source_manifest, create_run, finish_run
from .vector_store import ALIAS, cleanup_old_backups, collection_name_for_week, ensure_collection, swap_alias, upsert_points

logger = get_logger("rag.pipeline")

CONFIG_PATH = Path(__file__).parent / "config" / "sources.yaml"


def _load_sources() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    sources = [s for s in raw.get("sources", []) if s.get("enabled", True)]
    settings = raw.get("settings", {})
    return sources, settings


def _week_label() -> str:
    d = datetime.now(timezone.utc)
    y, w, _ = d.isocalendar()
    return f"{y}w{w:02d}"


def run_full_refresh(force: bool = False, week: str | None = None, db_path: Path | str | None = None) -> dict[str, Any]:
    week = week or _week_label()
    sources, settings = _load_sources()
    delay = float(settings.get("rate_limit", {}).get("default_delay_seconds", 1.5))
    respect_robots = bool(settings.get("rate_limit", {}).get("respect_robots", True))
    raw_dir = Path(settings.get("storage", {}).get("raw_dir", "data/rag/raw"))
    processed_dir = Path(settings.get("storage", {}).get("processed_dir", "data/rag/processed"))
    manifests_dir = Path(settings.get("storage", {}).get("manifests_dir", "data/rag/manifests"))
    manifests_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    embed_model = settings.get("vector_store", {}).get("embedding_model", "text-embedding-3-small")
    # collection for this week (unique per run to avoid collision if rerun same week)
    base_collection = collection_name_for_week(week)
    collection = base_collection
    # if exists and not force, add suffix
    from qdrant_client import QdrantClient
    import os

    # create run entry
    run_id = create_run(week=week, collection=collection, sources_manifest=[{"id": s["id"], "url": s["url"]} for s in sources], db_path=db_path)
    logger.info("RAG run %s start week=%s collection=%s", run_id, week, collection)

    all_docs: list[dict[str, Any]] = []
    source_stats: list[dict[str, Any]] = []

    try:
        # 1. Ingest
        for cfg in sources:
            try:
                docs = ingest_source(cfg, raw_dir=raw_dir, delay=delay, respect_robots=respect_robots)
            except Exception as e:
                logger.exception("ingest failed %s: %s", cfg["id"], e)
                docs = [{"source_id": cfg["id"], "url": cfg["url"], "text": "", "error": str(e), "priority": cfg.get("priority", 5)}]
            # stats
            ok_docs = [d for d in docs if d.get("text")]
            for d in docs:
                add_source_manifest(run_id, d.get("source_id", cfg["id"]), d.get("url", cfg["url"]), d.get("sha256"), d.get("etag"), 1 if d.get("text") else 0, 0, "ok" if d.get("text") else "error", db_path=db_path)
            all_docs.extend(ok_docs)
            source_stats.append({"id": cfg["id"], "docs": len(ok_docs), "total": len(docs)})

        if not all_docs:
            finish_run(run_id, status="failed", error="No docs fetched", db_path=db_path)
            return {"run_id": run_id, "status": "failed", "error": "No docs fetched"}

        # 2. Chunk
        chunks: list[dict[str, Any]] = []
        for d in all_docs:
            text = d.get("text", "")
            if not text or len(text) < 100:
                continue
            meta = {
                "source_id": d["source_id"],
                "source_url": d["url"],
                "title": d.get("title", d["source_id"]),
                "priority": d.get("priority", 5),
                "week": week,
            }
            chs = chunk_text(text, metadata=meta)
            chunks.extend(chs)
        chunks = dedupe_chunks(chunks)
        if not chunks:
            finish_run(run_id, status="failed", error="No chunks", db_path=db_path)
            return {"run_id": run_id, "status": "failed", "error": "No chunks"}

        # 3. Embed
        embedder = Embedder(model=embed_model)
        dim = embedder.dim
        # ensure collection
        # handle collision: if collection exists, recreate
        ensure_collection(collection, dim=dim, recreate=True)
        texts = [c["text"] for c in chunks]
        vectors = embedder.embed(texts)

        # 4. Upsert
        points = []
        for ch, vec in zip(chunks, vectors):
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ch['source_id']}:{ch['chunk_hash']}"))
            payload = {k: v for k, v in ch.items() if k != "text"}
            payload["text"] = ch["text"][:2000]  # store truncated for citation
            payload["week"] = week
            points.append({"id": pid, "vector": vec, "payload": payload})
        upsert_points(collection, points, batch_size=100)

        # save manifest & chunks
        manifest = {"week": week, "run_id": run_id, "collection": collection, "embed_model": embed_model, "embed_dim": dim, "provider": embedder.provider, "sources": source_stats, "chunks_total": len(chunks), "docs_total": len(all_docs)}
        (manifests_dir / f"{week}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (processed_dir / f"{week}.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks), encoding="utf-8")

        # 5. Swap alias (blue/green)
        swap_alias(collection)
        # 6. Cleanup old backups (>7 days)
        deleted = cleanup_old_backups(keep_days=7)

        status = "success" if len([s for s in source_stats if s["docs"] == 0]) == 0 else "partial"
        finish_run(run_id, status=status, docs_total=len(all_docs), chunks_total=len(chunks), db_path=db_path)
        logger.info("RAG run %s done status=%s chunks=%s alias->%s deleted=%s", run_id, status, len(chunks), collection, deleted)
        return {"run_id": run_id, "week": week, "collection": collection, "status": status, "docs_total": len(all_docs), "chunks_total": len(chunks), "deleted": deleted, "manifest": manifest}

    except Exception as e:
        logger.exception("RAG pipeline failed run %s: %s", run_id, e)
        finish_run(run_id, status="failed", error=str(e), db_path=db_path)
        raise
