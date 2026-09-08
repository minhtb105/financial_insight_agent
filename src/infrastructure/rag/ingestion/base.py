"""Base connector — rate-limit (no login), ETag, manifest."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from infrastructure.observability import get_logger

logger = get_logger("rag.ingestion")

DEFAULT_UA = "FinancialInsightAgent/1.0 (+https://finsight.vn/bot)"
DEFAULT_DELAY = 1.5


@dataclass
class FetchResult:
    source_id: str
    url: str
    content: bytes | str
    content_type: str
    etag: str | None
    sha256: str
    fetched_at: str
    status: str = "ok"
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def respect_robots(url: str, ua: str = DEFAULT_UA) -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(ua, url)
    except Exception:
        return True


def fetch_url(url: str, delay: float = DEFAULT_DELAY, ua: str = DEFAULT_UA, timeout: int = 30, respect_robots_flag: bool = True) -> FetchResult:
    if respect_robots_flag and not respect_robots(url, ua):
        return FetchResult(source_id="", url=url, content=b"", content_type="", etag=None, sha256="", fetched_at="", status="blocked_robots", error="Blocked by robots.txt")
    time.sleep(delay)
    headers = {"User-Agent": ua, "Accept": "*/*"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        etag = resp.headers.get("etag")
        # content handling
        if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
            data = resp.content
            sha = sha256_bytes(data)
            return FetchResult(source_id="", url=url, content=data, content_type=ctype or "application/pdf", etag=etag, sha256=sha, fetched_at="", status="ok")
        else:
            text = resp.text
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            return FetchResult(source_id="", url=url, content=text, content_type=ctype or "text/html", etag=etag, sha256=sha, fetched_at="", status="ok")
    except Exception as e:
        logger.warning("fetch failed %s: %s", url, e)
        return FetchResult(source_id="", url=url, content=b"", content_type="", etag=None, sha256="", fetched_at="", status="error", error=str(e))
