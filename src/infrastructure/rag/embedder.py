"""Embedder — OpenAI text-embedding-3-small primary, sentence-transformers fallback."""

from __future__ import annotations

import os

from infrastructure.observability import get_logger

logger = get_logger("rag.embedder")


class Embedder:
    def __init__(self, model: str | None = None, dim: int = 1536):
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.dim = dim
        self._openai_client = None
        self._st_model = None
        self._init_clients()

    def _init_clients(self) -> None:
        key = os.getenv("OPENAI_API_KEY")
        if key:
            try:
                from openai import OpenAI

                self._openai_client = OpenAI(api_key=key)
            except Exception as e:
                logger.warning("OpenAI embed init failed: %s", e)
        if not self._openai_client:
            # fallback local
            try:
                from sentence_transformers import SentenceTransformer

                # multilingual for Vietnamese
                self._st_model = SentenceTransformer("intfloat/multilingual-e5-base")
                self.dim = 768
                logger.info("Using sentence-transformers fallback, dim=768")
            except Exception as e:
                logger.warning("sentence-transformers init failed: %s", e)

    @property
    def provider(self) -> str:
        if self._openai_client:
            return "openai"
        if self._st_model:
            return "sentence_transformers"
        return "none"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._openai_client:
            try:
                # batch size 100 to avoid token limit
                out: list[list[float]] = []
                for i in range(0, len(texts), 100):
                    batch = texts[i : i + 100]
                    resp = self._openai_client.embeddings.create(model=self.model, input=batch)
                    for d in resp.data:
                        out.append(d.embedding)
                return out
            except Exception as e:
                logger.warning("OpenAI embed failed, trying fallback: %s", e)
                if self._st_model:
                    return self._st_model.encode(texts, normalize_embeddings=True).tolist()  # type: ignore
                raise
        if self._st_model:
            return self._st_model.encode(texts, normalize_embeddings=True).tolist()  # type: ignore
        raise RuntimeError("No embedding provider available — set OPENAI_API_KEY or install sentence-transformers")


def embed_query(query: str, embedder: Embedder | None = None) -> list[float]:
    emb = embedder or Embedder()
    return emb.embed([query])[0]
