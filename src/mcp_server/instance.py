"""MCP instance — single FastMCP singleton."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.config import MCP_NAME, MCP_HOST, MCP_PORT

mcp = FastMCP(
    name=MCP_NAME,
    instructions="Financial Insight MCP — 13 tools: live market data (vnstock) + RAG knowledge (VBPL/TT/SSI/HNX/HOSE). Each tool has JSONSchema for auto-discovery via tools/list.",
    host=MCP_HOST,
    port=MCP_PORT,
)
