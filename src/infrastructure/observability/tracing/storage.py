"""Persistence layer for traces: SQLite primary store + optional JSONL mirror."""

from __future__ import annotations

import contextlib
import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    request_id TEXT,
    root_name TEXT,
    status TEXT DEFAULT 'running',
    started_at REAL,
    ended_at REAL,
    duration_ms REAL,
    num_spans INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    llm_call_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    parent_span_id TEXT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    request_id TEXT,
    started_at REAL,
    ended_at REAL,
    duration_ms REAL,
    status TEXT,
    model TEXT,
    provider TEXT,
    prompt_name TEXT,
    prompt_version TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    inputs TEXT,
    outputs TEXT,
    attributes TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_started ON traces(started_at DESC);
"""


class TraceStore:
    """Thread-safe SQLite storage for spans and trace summaries."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, timeout=30
        )
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def record_span(
        self,
        span_dict: dict[str, Any],
        inputs_json: str | None,
        outputs_json: str | None,
        attributes_json: str | None,
        is_root: bool,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO spans (
                    span_id, trace_id, parent_span_id, name, kind, request_id,
                    started_at, ended_at, duration_ms, status, model, provider,
                    prompt_name, prompt_version, prompt_tokens, completion_tokens,
                    total_tokens, inputs, outputs, attributes, error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    span_dict["span_id"],
                    span_dict["trace_id"],
                    span_dict["parent_span_id"],
                    span_dict["name"],
                    span_dict["kind"],
                    span_dict["request_id"],
                    span_dict["started_at"],
                    span_dict["ended_at"],
                    span_dict["duration_ms"],
                    span_dict["status"],
                    span_dict["model"],
                    span_dict["provider"],
                    span_dict["prompt_name"],
                    span_dict["prompt_version"],
                    span_dict["prompt_tokens"],
                    span_dict["completion_tokens"],
                    span_dict["total_tokens"],
                    inputs_json,
                    outputs_json,
                    attributes_json,
                    span_dict["error"],
                ),
            )
            self._upsert_trace(span_dict, is_root)
            self._refresh_trace_aggregates(span_dict["trace_id"])
            if is_root:
                self._conn.execute(
                    "UPDATE traces SET status=?, ended_at=?, duration_ms=? WHERE trace_id=?",
                    (
                        span_dict["status"],
                        span_dict["ended_at"],
                        span_dict["duration_ms"],
                        span_dict["trace_id"],
                    ),
                )
            self._conn.commit()

    def _upsert_trace(self, span_dict: dict[str, Any], is_root: bool) -> None:
        root_name = span_dict["name"] if is_root else None
        self._conn.execute(
            """
            INSERT INTO traces (trace_id, request_id, root_name, status, started_at)
            VALUES (?,?,?, 'running', ?)
            ON CONFLICT(trace_id) DO UPDATE SET
                root_name = COALESCE(root_name, excluded.root_name),
                request_id = COALESCE(request_id, excluded.request_id)
            """,
            (
                span_dict["trace_id"],
                span_dict["request_id"],
                root_name,
                span_dict["started_at"],
            ),
        )

    def _refresh_trace_aggregates(self, trace_id: str) -> None:
        self._conn.execute(
            """
            UPDATE traces SET
                num_spans = (SELECT COUNT(*) FROM spans WHERE trace_id=:tid),
                total_tokens = (SELECT COALESCE(SUM(total_tokens), 0) FROM spans WHERE trace_id=:tid),
                llm_call_count = (SELECT COUNT(*) FROM spans WHERE trace_id=:tid AND kind='llm'),
                tool_call_count = (SELECT COUNT(*) FROM spans WHERE trace_id=:tid AND kind='tool')
            WHERE trace_id=:tid
            """,
            {"tid": trace_id},
        )

    def purge_older_than(self, days: int) -> int:
        cutoff = time.time() - days * 86400
        with self._lock:
            cur = self._conn.execute("SELECT trace_id FROM traces WHERE started_at < ?", (cutoff,))
            ids = [r[0] for r in cur.fetchall()]
            for tid in ids:
                self._conn.execute("DELETE FROM spans WHERE trace_id=?", (tid,))
                self._conn.execute("DELETE FROM traces WHERE trace_id=?", (tid,))
            self._conn.commit()
        return len(ids)

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.commit()
                self._conn.close()
            except sqlite3.Error:
                pass

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_span(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for key in ("inputs", "outputs", "attributes"):
            raw = d.get(key)
            if isinstance(raw, str):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d[key] = json.loads(raw)
        return d

    def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        min_duration_ms: float | None = None,
        name_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM traces WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if min_duration_ms is not None:
            query += " AND duration_ms >= ?"
            params.append(min_duration_ms)
        if name_filter:
            query += " AND root_name LIKE ?"
            params.append(f"%{name_filter}%")
        query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._lock:
            trow = self._conn.execute(
                "SELECT * FROM traces WHERE trace_id=?", (trace_id,)
            ).fetchone()
            if trow is None:
                return None
            srows = self._conn.execute(
                "SELECT * FROM spans WHERE trace_id=? ORDER BY started_at ASC",
                (trace_id,),
            ).fetchall()
        trace = dict(trow)
        trace["spans"] = [self._row_to_span(r) for r in srows]
        return trace


class JSONLExporter:
    """Appends finished span dicts as JSON lines to a file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, span_dict: dict[str, Any]) -> None:
        line = json.dumps(span_dict, ensure_ascii=False, default=str)
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
