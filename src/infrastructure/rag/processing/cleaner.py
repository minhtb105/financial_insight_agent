"""Clean raw HTML/PDF text for chunking."""

from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+")
_CITE_RE = re.compile(r"\[\s*TICKER:.*?\]", re.IGNORECASE)


def clean_text(text: str) -> str:
    if not text:
        return ""
    # unicode normalize
    text = unicodedata.normalize("NFC", text)
    # remove excessive whitespace
    text = _WS_RE.sub(" ", text)
    # trim per line
    lines = [l.strip() for l in text.splitlines()]
    # drop empty lines
    lines = [l for l in lines if l]
    out = "\n".join(lines)
    # collapse multiple newlines
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def truncate(text: str, max_chars: int = 50000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"
