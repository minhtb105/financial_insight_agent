"""MCP tool loader — agent auto-discovers via tools/list (MCP spec)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from infrastructure.observability import get_logger

logger = get_logger("mcp.loader")

MCP_URL = os.getenv("MCP_URL", os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp"))
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")  # stdio | sse | streamable-http | http


def _connections_config() -> dict[str, Any]:
    # prod: streamable-http via :8001/mcp, dev: stdio
    if MCP_TRANSPORT == "stdio":
        return {
            "finsight": {
                "command": "python",
                "args": ["-m", "mcp_server.server", "--transport", "stdio"],
                "transport": "stdio",
            }
        }
    # For SSE/streamable-http, langchain-mcp-adapters expects "url" + "transport": "streamable_http" or "sse"
    # Normalize transport naming
    transport = MCP_TRANSPORT
    if transport == "streamable-http":
        transport = "streamable_http"
    # default http maps to streamable_http in new adapter
    if transport == "http":
        transport = "streamable_http"
    return {
        "finsight": {
            "url": MCP_URL,
            "transport": transport,
        }
    }


async def _load_mcp_tools_async() -> list[Any]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(_connections_config())
    tools = await client.get_tools()
    # Keep client alive for tool calls? Adapter keeps session per call (stateless)
    # So we don't need to hold session.
    logger.info("MCP loader got %d tools via tools/list from %s", len(tools), MCP_URL)
    return tools


def load_mcp_tools_sync() -> list[Any]:
    """Sync wrapper — tries MCP, falls back to in-process mcp_server.tools."""
    # Try MCP network first (if server is reachable)
    try:
        # Use get_event_loop if exists, else new
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # Already running loop (e.g. FastAPI) — create new thread loop
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                fut = pool.submit(asyncio.run, _load_mcp_tools_async())
                return fut.result(timeout=5)
        else:
            # No running loop — with quick timeout via wait_for
            try:
                return asyncio.run(asyncio.wait_for(_load_mcp_tools_async(), timeout=5))
            except asyncio.TimeoutError:
                raise TimeoutError("MCP load timeout after 5s")
    except Exception as e:
        logger.warning("MCP load failed (%s), falling back to in-process tools: %s", MCP_URL, e)
        # Fallback: import directly from mcp_server (in-process) — still exercises MCP definitions
        try:
            from mcp_server.instance import mcp as mcp_instance
            import mcp_server.tools  # ensure registered  # noqa: F401

            # Convert FastMCP tools to LangChain tools via adapter helper
            # FastMCP's _tool_manager holds Tool objects; we can convert manually
            # Simpler: use langchain_mcp_adapters.tools.load_mcp_tools on a dummy session
            # Fallback: build LangChain StructuredTool from mcp tool definitions directly
            from langchain_core.tools import StructuredTool

            tools: list[Any] = []
            for name, tool in mcp_instance._tool_manager._tools.items():
                fn = getattr(tool, "fn", None) or getattr(tool, "_func", None)
                if fn is None:
                    # FastMCP 1.27 stores callable in .fn or ._fn
                    fn = getattr(tool, "callable", None)
                if fn is None:
                    continue
                try:
                    from langchain_core.tools import StructuredTool

                    st = StructuredTool.from_function(
                        func=fn,
                        name=name,
                        description=tool.description or "",
                    )
                    tools.append(st)
                except Exception as e:
                    logger.warning("Failed to convert tool %s: %s", name, e)
                    continue
            if tools:
                logger.info("Fallback in-process loaded %d tools", len(tools))
                return tools
        except Exception as fe:
            logger.warning("Fallback also failed: %s", fe)

        # Last resort: import legacy ALL_TOOLS if still exists (should not per spec, but for dev)
        try:
            from mcp_server.tools.helpers import call_service  # noqa: F401

            # Try to import via mcp_server tools directly as langchain tools
            # If all else fails, return empty and let agent run in degraded mode
            logger.error("No tools available after MCP + fallback")
            return []
        except Exception:
            return []
