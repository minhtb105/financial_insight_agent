"""HTML to markdown/text."""

from __future__ import annotations

import re


def html_to_text(html: str) -> str:
    # try html2text, fallback BeautifulSoup
    try:
        import html2text

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0
        return h.handle(html)
    except Exception:
        pass
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n")
    except Exception:
        # naive strip
        return re.sub(r"<[^>]+>", " ", html)
