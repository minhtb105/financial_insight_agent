# MCP Server — Financial Insight

> Agent kết nối MCP qua `tools/list` tự động học 13 tools, không còn hướng dẫn tool trong prompt (tối ưu prompt caching).

## Kiến trúc

- **Server:** `src/mcp_server/` (FastMCP official `mcp>=1.9`), 13 tools strict `Literal` cho 5 tool đầu (`field`, `indicator`, `aggregate`)
- **Transports:** `stdio` (dev, Claude Desktop) và `streamable-http :8001/mcp` (prod)
- **Client:** `src/infrastructure/mcp/loader.py` `MultiServerMCPClient` → `client.get_tools()` → `LLMChain.bind_tools`
- **Prompt:** `agent_system` v1.2 213t (giảm -68% so với v1.1 684t), tách `SystemMessage` static (cacheable) vs dynamic (date+memory)

## Tools

13 tools trong `src/mcp_server/tools/` — mỗi file 1 tool, schema JSON từ `Annotated[Literal[...]]`:
- `price`, `indicator`, `compare`, `ranking`, `aggregate` (strict enums)
- `financial_ratios`, `company`, `news`, `portfolio`, `alerts`, `forecast`, `sector`, `knowledge` (via `KnowledgePort` → Qdrant)

## Chạy

```bash
# Dev stdio (Claude Desktop)
python -m mcp_server.server --transport stdio

# Dev HTTP
python -m mcp_server.server --transport streamable-http --host 0.0.0.0 --port 8001
# Test tools/list
curl -H "Content-Type: application/json" http://localhost:8001/mcp -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Docker
docker compose up mcp_server backend
docker compose -f docker-compose.dev.yml up mcp_server
```

## Env

- `MCP_URL=http://mcp_server:8001/mcp` (prod) / `http://localhost:8001/mcp` (local)
- `MCP_TRANSPORT=streamable-http|stdio|ssek`
- `QDRANT_HOST`, `OPENAI_API_KEY`

## Agent

`src/application/agents/agent.py:64` → `load_mcp_tools_sync()` (thử MCP network, fallback in-process). `src/shared/ports/` cung cấp `MarketDataPort`, `KnowledgePort`, `CachePort` — services không import `infrastructure` trực tiếp nữa (qua `src/infrastructure/adapters/`).

## Cấu trúc lại

```
src/shared/ports/*  +  src/infrastructure/adapters/*  +  src/mcp_server/tools/*  +  src/application/use_cases/*
tests/unit/mcp_server/test_mcp_tools.py (thay test_tool_registry)
```

## Verify

```bash
pytest src/tests/unit/mcp_server/test_mcp_tools.py -v
python -c "import sys; sys.path.insert(0,'src'); from mcp_server.instance import mcp; import mcp_server.tools; print(len(mcp._tool_manager._tools))"
```
