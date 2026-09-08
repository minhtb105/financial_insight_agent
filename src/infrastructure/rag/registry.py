"""SQLite registry for RAG ingestion runs — tracks weekly full replace."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("data/rag/registry.db")


def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    p = Path(db_path) if db_path else DEFAULT_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ingestion_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL, -- running, success, partial, failed
                collection TEXT,
                docs_total INTEGER DEFAULT 0,
                chunks_total INTEGER DEFAULT 0,
                sources_manifest TEXT, -- JSON
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS source_manifests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER REFERENCES ingestion_runs(id),
                source_id TEXT NOT NULL,
                url TEXT,
                sha256 TEXT,
                etag TEXT,
                fetched_at TEXT,
                doc_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                status TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_runs_week ON ingestion_runs(week);
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_run(week: str, collection: str, sources_manifest: list[dict[str, Any]] | None = None, db_path: Path | str | None = None) -> int:
    init_db(db_path)
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO ingestion_runs (week, started_at, status, collection, sources_manifest) VALUES (?, ?, ?, ?, ?)",
            (week, datetime.now(timezone.utc).isoformat(), "running", collection, json.dumps(sources_manifest or [], ensure_ascii=False)),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def finish_run(run_id: int, status: str, docs_total: int = 0, chunks_total: int = 0, error: str | None = None, db_path: Path | str | None = None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE ingestion_runs SET finished_at=?, status=?, docs_total=?, chunks_total=?, error=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), status, docs_total, chunks_total, error, run_id),
        )
        conn.commit()
    finally:
        conn.close()


def add_source_manifest(run_id: int, source_id: str, url: str, sha256: str | None, etag: str | None, doc_count: int, chunk_count: int, status: str, db_path: Path | str | None = None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO source_manifests (run_id, source_id, url, sha256, etag, fetched_at, doc_count, chunk_count, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, source_id, url, sha256, etag, datetime.now(timezone.utc).isoformat(), doc_count, chunk_count, status),
        )
        conn.commit()
    finally:
        conn.close()


def get_last_runs(limit: int = 10, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM ingestion_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run(run_id: int, db_path: Path | str | None = None) -> dict[str, Any] | None:
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT * FROM ingestion_runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
