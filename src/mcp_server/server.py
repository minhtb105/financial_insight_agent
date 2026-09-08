"""MCP server entry — dual transport stdio / streamable-http."""

from __future__ import annotations

import argparse
import sys

from mcp_server.instance import mcp

# Import all tools to register them
import mcp_server.tools  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(description="Finsight MCP server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio", help="Transport")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    # Ensure strict DI services are initialized (ports + registry)
    try:
        from infrastructure.dependencies import init_deps

        init_deps()
    except Exception:
        pass

    # Override host/port if provided
    if args.host:
        mcp.settings.host = args.host  # type: ignore
    if args.port:
        mcp.settings.port = args.port  # type: ignore

    # stdio: no host/port
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse")
    else:
        # streamable-http is the spec name; FastMCP maps to streamable-http
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    # Allow `python -m mcp_server.server --transport stdio`
    # Also support `python src/mcp_server/server.py`
    sys.path.insert(0, "src")
    main()
