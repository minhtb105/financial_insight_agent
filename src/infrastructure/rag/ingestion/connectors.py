"""Unified ingestion entry — per source config."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from infrastructure.observability import get_logger
from .base import fetch_url
from .crawler import crawl
from .html_parser import html_to_text
from .pdf_parser import pdf_bytes_to_text
from ..processing.cleaner import clean_text

logger = get_logger("rag.connectors")


def ingest_source(cfg: dict[str, Any], raw_dir: Path, delay: float = 1.5, respect_robots: bool = True) -> list[dict[str, Any]]:
    sid = cfg["id"]
    url = cfg["url"]
    stype = cfg.get("type", "html")
    # ensure raw dir
    out_dir = raw_dir / sid
    out_dir.mkdir(parents=True, exist_ok=True)

    docs: list[dict[str, Any]] = []

    if stype == "pdf":
        urls = [url]
        if cfg.get("fallback_url"):
            urls.append(cfg["fallback_url"])
        fetched = None
        for u in urls:
            fr = fetch_url(u, delay=delay, respect_robots_flag=respect_robots)
            if fr.status == "ok":
                fetched = fr
                fetched.source_id = sid
                break
            else:
                logger.warning("pdf fetch failed %s: %s", u, fr.error)
        if not fetched or fetched.status != "ok":
            return [{"source_id": sid, "url": url, "text": "", "error": "fetch failed", "priority": cfg.get("priority", 5)}]
        data = fetched.content if isinstance(fetched.content, (bytes, bytearray)) else str(fetched.content).encode()
        text = pdf_bytes_to_text(bytes(data))
        text = clean_text(text)
        # save raw pdf
        try:
            (out_dir / f"{sid}.pdf").write_bytes(bytes(data))
        except Exception:
            pass
        docs.append({"source_id": sid, "url": fetched.url, "text": text, "priority": cfg.get("priority", 5), "title": cfg.get("name", sid), "sha256": fetched.sha256, "etag": fetched.etag})

    elif stype in ("html", "generic_html"):
        fr = fetch_url(url, delay=delay, respect_robots_flag=respect_robots)
        if fr.status != "ok":
            return [{"source_id": sid, "url": url, "text": "", "error": fr.error, "priority": cfg.get("priority", 5)}]
        html = fr.content if isinstance(fr.content, str) else fr.content.decode("utf-8", errors="ignore")
        text = clean_text(html_to_text(html))
        docs.append({"source_id": sid, "url": fr.url, "text": text, "priority": cfg.get("priority", 5), "title": cfg.get("name", sid), "sha256": fr.sha256, "etag": fr.etag})

    elif stype == "html_crawl":
        crawl_cfg = cfg.get("crawl", {})
        max_pages = int(crawl_cfg.get("max_pages", 30))
        pages = crawl(url, max_pages=max_pages, delay=delay, respect_robots_flag=respect_robots)
        for p in pages:
            text = clean_text(html_to_text(p["html"]))
            if len(text) < 200:
                continue
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            docs.append({"source_id": sid, "url": p["url"], "text": text, "priority": cfg.get("priority", 5), "title": cfg.get("name", sid), "sha256": sha, "etag": None})
        if not docs:
            docs.append({"source_id": sid, "url": url, "text": "", "error": "no pages", "priority": cfg.get("priority", 5)})

    else:
        logger.warning("unknown source type %s for %s", stype, sid)
        docs.append({"source_id": sid, "url": url, "text": "", "error": f"unknown type {stype}", "priority": cfg.get("priority", 5)})

    return docs
