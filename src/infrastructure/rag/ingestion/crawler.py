"""Simple crawler for html_crawl sources — respects robots, rate-limit, no login."""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from infrastructure.observability import get_logger
from .base import DEFAULT_DELAY, DEFAULT_UA, fetch_url, respect_robots

logger = get_logger("rag.crawler")


def crawl(start_url: str, max_pages: int = 30, delay: float = DEFAULT_DELAY, ua: str = DEFAULT_UA, respect_robots_flag: bool = True) -> list[dict[str, str]]:
    visited: set[str] = set()
    queue: list[str] = [start_url]
    results: list[dict[str, str]] = []
    base_netloc = urlparse(start_url).netloc

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if respect_robots_flag and not respect_robots(url, ua):
            logger.info("skip robots blocked %s", url)
            continue
        time.sleep(delay)
        fr = fetch_url(url, delay=0, ua=ua, respect_robots_flag=False)  # already checked
        if fr.status != "ok":
            continue
        html = fr.content if isinstance(fr.content, str) else fr.content.decode("utf-8", errors="ignore")
        results.append({"url": url, "html": html})
        # discover links (same domain)
        try:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]  # type: ignore
                nxt = urljoin(url, href)
                if urlparse(nxt).netloc != base_netloc:
                    continue
                if nxt in visited or nxt in queue:
                    continue
                # filter common non-content
                if any(x in nxt.lower() for x in [".pdf", ".jpg", ".png", "logout", "login"]):
                    continue
                if len(queue) + len(results) < max_pages:
                    queue.append(nxt)
        except Exception:
            continue
    return results
