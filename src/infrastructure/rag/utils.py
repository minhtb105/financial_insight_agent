"""RAG shared utils — single source for week label."""

from __future__ import annotations

from datetime import datetime, timezone


def week_label(dt: datetime | None = None) -> str:
    """Return ISO week label ``YYYYwWW`` for *dt* (UTC)."""
    d = dt or datetime.now(timezone.utc)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    year, week, _ = d.isocalendar()
    return f"{year}w{week:02d}"
