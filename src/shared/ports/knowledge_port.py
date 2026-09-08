"""KnowledgePort — abstraction for RAG search."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class KnowledgePort(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5, min_score: float = 0.3) -> dict[str, Any]:
        """Return {hits:[{score,payload}], context:str, count:int}."""
