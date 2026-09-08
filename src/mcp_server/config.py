"""MCP server config."""

from __future__ import annotations

import os

MCP_NAME = os.getenv("MCP_NAME", "finsight-mcp")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
MCP_SSE_PATH = os.getenv("MCP_SSE_PATH", "/sse")
MCP_STREAMABLE_PATH = os.getenv("MCP_STREAMABLE_PATH", "/mcp")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
