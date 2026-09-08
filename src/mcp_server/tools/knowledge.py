"""MCP tool: search_knowledge — via KnowledgePort/Qdrant."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service, _safe_json
from infrastructure.adapters.knowledge_adapter import QdrantKnowledgeAdapter

_adapter = QdrantKnowledgeAdapter()


@mcp.tool(
    name="search_knowledge",
    description="Search knowledge base for Vietnamese securities law/regulation/education (Luật CK 24/VBHN-VPQH, TT96, TT135, SSI, HNX/HOSE). Returns citations [Nguồn: Tên - Điều - URL] with priority. ALWAYS include citations in answer. NEVER use for live prices/ratios — use market tools there. Priority: VBPL(1) > TT(2) > HNX/HOSE(3) > SSI(4) > intl(5). Safety: educational only, not licensed advice.",
)
def search_knowledge(
    query: Annotated[str, Field(description="Vietnamese query about law/concept")],
    top_k: Annotated[int, Field(description="Top K hits", ge=1, le=10)] = 5,
) -> str:
    try:
        result = _adapter.search(query, top_k=top_k)
        # _adapter returns dict with hits/context — wrap via _safe_json
        import json

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        from mcp_server.tools.helpers import _categorize_error

        return _categorize_error(e)
