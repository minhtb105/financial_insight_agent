"""Chunker for RAG — recursive splitter with metadata preservation."""

from __future__ import annotations

import hashlib
from typing import Any

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # new import
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # fallback

DEFAULT_CHUNK_SIZE = 700
DEFAULT_OVERLAP = 80


def chunk_text(
    text: str,
    metadata: dict[str, Any],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict[str, Any]]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap, separators=["\n\n", "\n", ". ", " ", ""])
    chunks = splitter.split_text(text)
    out = []
    for idx, ch in enumerate(chunks):
        h = hashlib.sha256(ch.encode("utf-8")).hexdigest()[:16]
        payload = dict(metadata)
        payload.update({"chunk_index": idx, "chunk_hash": h, "text": ch})
        out.append(payload)
    return out


def dedupe_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out = []
    for c in chunks:
        h = c.get("chunk_hash")
        if h in seen:
            continue
        seen.add(h)  # type: ignore
        out.append(c)
    return out
