"""Central application config — single source for env parsing.

Replaces scattered ``os.getenv`` across 8 locations. ``shared/constants.py``
re-exports TTLs for backward compat, but new code should import from here.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# TTLs (hours) — used by services via shared.constants (re-export) and
# infrastructure.cache.config tier mapping.
# ---------------------------------------------------------------------------
PRICE_TTL_HOURS: float = _get_float("PRICE_TTL_HOURS", 0.5)
INDICATOR_TTL_HOURS: float = _get_float("INDICATOR_TTL_HOURS", 0.5)
FORECAST_TTL_HOURS: float = _get_float("FORECAST_TTL_HOURS", 1)
NEWS_TTL_HOURS: float = _get_float("NEWS_TTL_HOURS", 1)
COMPANY_TTL_HOURS: float = _get_float("COMPANY_TTL_HOURS", 4)
RATIO_TTL_HOURS: float = _get_float("RATIO_TTL_HOURS", 2)
SECTOR_TTL_HOURS: float = _get_float("SECTOR_TTL_HOURS", 2)
PORTFOLIO_TTL_HOURS: float = _get_float("PORTFOLIO_TTL_HOURS", 0.25)

# Cache tiers (mirror infrastructure/cache/config.py defaults for documentation)
CACHE_L1_TTL_HOURS: float = _get_float("CACHE_L1_TTL_HOURS", 0.5)
CACHE_L2_TTL_HOURS: float = _get_float("CACHE_L2_TTL_HOURS", 2)
SESSION_TTL_HOURS: float = _get_float("SESSION_TTL_HOURS", 24)

# ---------------------------------------------------------------------------
# Core services
# ---------------------------------------------------------------------------
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
HUGGINGFACEHUB_API_TOKEN: str | None = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Qdrant
QDRANT_HOST: str = os.getenv("QDRANT_HOST", "qdrant" if os.getenv("QDRANT_HOST") else "localhost")
QDRANT_PORT: int = _get_int("QDRANT_PORT", 6333)
QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")
QDRANT_EXTERNAL_PORT: int = _get_int("QDRANT_EXTERNAL_PORT", 6333)
QDRANT_GRPC_PORT: int = _get_int("QDRANT_GRPC_PORT", 6334)

# Redis
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = _get_int("REDIS_PORT", 6379)

# MCP
MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT: int = _get_int("MCP_PORT", 8001)
MCP_SSE_PATH: str = os.getenv("MCP_SSE_PATH", "/sse")
MCP_STREAMABLE_PATH: str = os.getenv("MCP_STREAMABLE_PATH", "/mcp")
MCP_URL: str = os.getenv("MCP_URL", f"http://localhost:{MCP_PORT}{MCP_STREAMABLE_PATH}")
MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "streamable-http")
MCP_EXTERNAL_PORT: int = _get_int("MCP_EXTERNAL_PORT", 8001)

# FastAPI
APP_PORT: int = _get_int("APP_PORT", 8000)
APP_EXTERNAL_PORT: int = _get_int("APP_EXTERNAL_PORT", 8000)
FRONTEND_EXTERNAL_PORT: int = _get_int("FRONTEND_EXTERNAL_PORT", 3000)
ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://frontend:3000")
ENABLE_RAG_SCHEDULER: bool = _get_bool("ENABLE_RAG_SCHEDULER", True)
ADMIN_API_KEY: str | None = os.getenv("ADMIN_API_KEY")

# NextAuth / Frontend
NEXTAUTH_SECRET: str | None = os.getenv("NEXTAUTH_SECRET")
NEXTAUTH_URL: str = os.getenv("NEXTAUTH_URL", "http://localhost:3000")
API_URL: str = os.getenv("API_URL", "http://localhost:8000")
NEXT_PUBLIC_API_URL: str = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")

# Observability
LANGSMITH_TRACING: bool = _get_bool("LANGSMITH_TRACING", False)
LANGSMITH_API_KEY: str | None = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "financial_insight_agent")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Agent
AGENT_MAX_ITERATIONS: int = _get_int("AGENT_MAX_ITERATIONS", 10)
AGENT_TIMEOUT_SECONDS: int = _get_int("AGENT_TIMEOUT_SECONDS", 120)
