# Financial Insight Agent — Onboarding Guide

> **Generated from knowledge graph** `\.ua/knowledge-graph.json` (331 files, 1278 nodes, 2370 edges, commit `bada90f`) — run `/understand` to refresh after source changes.
> **Languages:** python, typescript, javascript, markdown, yaml, json, dockerfile, css | **Frameworks:** LangGraph, LangChain, FastAPI, Pydantic, SQLAlchemy, MCP, React, Qdrant
> **Description:** An AI-powered question-answering agent that retrieves company information and historical stock data from vnstock, with support for SMA and RSI indicators through a REST API.

---

## Project Overview

| Field | Value |
|-------|-------|
| **Name** | `financial_insight_agent` (`pyproject.toml:6`) |
| **Version** | `0.1.1` (`pyproject.toml:7`) |
| **Python** | `3.13` (ruff `pyproject.toml:105`, mypy `pyproject.toml:166`) |
| **Core stacks** | `langgraph>=0.5`, `langchain>=0.3.27`, `fastapi>=0.121.1`, `pydantic>=2`, `vnstock>=3.0.0`, `qdrant-client>=1.11.0`, `sentence-transformers`, `mcp>=1.9`, `sqlalchemy[asyncio]`, `redis>=5` (`pyproject.toml:13-50`) |
| **Entry points** | `src/interfaces/api/app.py:217` (FastAPI lifespan), `src/interfaces/cli/console.py`, `langgraph.json:6` (`build_graph`) |
| **Purpose** | Vietnamese stock Q&A ReAct agent — 12 query types (price, indicator SMA/RSI, company, compare, ranking, aggregate, financial ratio, news sentiment, portfolio, alert, forecast, sector) with input/output guardrails, circuit breaker, Redis caching, structured logging, metrics and rate limiting (`README.md:12-14`). Shift from demo to cited educational finance gateway (citation_rate / RAGAS eval harness `evals/`, 36 golden cases). |

**Quickstart:**
```bash
py -m venv .venv; .\.venv\Scripts\Activate.ps1   # Windows (Linux: source .venv/bin/activate)
pip install -U pip; pip install -e ".[dev]"
cp .env.example .env  # set OPENAI_API_KEY or GROQ_API_KEY, ALLOWED_ORIGINS, ADMIN_API_KEY, DB_URL
# optional RAG seed
python -m infrastructure.rag.cli run --force
uvicorn src.interfaces.api.app:app --reload --port 8000  # http://localhost:8000/docs
pytest src/tests -v
```

---

## Architecture Layers

> 8 layers derived from `\.ua/knowledge-graph.json` (336 file-level nodes). Layers are directory + type driven; clean architecture `domain → application → infrastructure → interfaces` with shared kernel.

### 1) Domain Layer — 5 nodes `layer:domain:5`
**Purpose:** Pure business entities, no I/O. Defines ubiquitous language for queries.
**Key files:**
- `src/domain/entities/time_range.py` — `HistoricalQuery`, `Interval`, `RequestedField`
- `src/domain/schemas/price.py` — 12 Pydantic models (price, indicator, compare, ranking, aggregate, financial ratio, company, news_sentiment, portfolio, alert, forecast, sector)
- `src/domain/entities/__init__.py`, `src/domain/schemas/__init__.py`

### 2) Application Layer — 30 nodes `layer:application:30`
**Purpose:** Use cases & orchestration. ReAct agent + 12 service handlers.
**Key files:**
- `src/application/agents/agent.py:63` — `StockAgent` (StateGraph `reason↔action↔final_answer→verify_facts`, `MemorySaver` checkpoint, `HybridQuerySplitter`, `ResponseSynthesizer`, `FactVerifier` 0.8, prompt-cache split static/dynamic `agent.py:192`, SSE threading `agent.py:416`)
- `src/application/agents/hybrid_splitter.py:1` — rule-based + LLM fallback splitter
- `src/application/agents/custom_tool_node.py:1`, `multi_query_runner.py:1`, `fact_verifier.py:1`, `response_synthesizer.py:1`
- `src/application/prompts/registry.py` + `templates/agent_system.yaml` (citation `[Nguồn: ...]`, TT135 safety)
- `src/application/services/market/{price,indicator,compare,alert,forecast,sector}_service.py`
- `src/application/services/financial/{aggregate,financial_ratio,ranking}_service.py`
- `src/application/services/company/company_service.py`, `src/application/services/portfolio/{portfolio,news_sentiment}_service.py`
- Extends `src/shared/base_service.py:20` (`for_each_ticker` ThreadPool 5/16, 30s per-ticker, 120s overall `base_service.py:38`).

### 3) Infrastructure Layer — 79 nodes `layer:infrastructure:79`
**Purpose:** Adapters, external clients, cross-cutting concerns (largest layer).
**Sub-areas:**
- **API clients:** `src/infrastructure/api_clients/vn_stock_client.py`
- **Adapters (ports):** `src/infrastructure/adapters/{vn_stock,company,financial,news,knowledge,cache}_adapter.py` → `shared/ports/{cache_port,market_data_port}.py`
- **Cache:** `src/infrastructure/cache/{cache_manager,memory_cache,redis_cache,cache_keys,serialization,session_manager,config}.py` (L1 memory + L2 Redis)
- **LLM:** `src/infrastructure/llm/llm_provider.py` (OpenAI primary, Groq fallback, `get_tool_calling_llm(tools)` bound to MCP schemas)
- **Guardrails:** `src/infrastructure/guardrails/{pipeline,content_filter,query_validator,rate_limiter,tickers,output_guardrails}.py` — 5-stage pipeline `RateLimiter → QuerySizeLimit → ContentFilter → TickerValidator → PatternGuard` fail-closed `pipeline.py:30`
- **Resilience:** `src/infrastructure/resilience/circuit_breaker.py`
- **Memory:** `src/infrastructure/memory/{memory_manager,short_term/memory}.py` (top_k 3 `agent.py:487`)
- **Observability:** `src/infrastructure/observability/{logging/logger,tracing/{tracer,storage,context,langchain_handler,models},metrics/collector,alerting/manager}.py` — `request_id_var` ContextVar `agent.py:504`
- **RAG:** `src/infrastructure/rag/{pipeline,embedder,retriever,vector_store,scheduler,ingestion/{base,connectors,crawler,html_parser,pdf_parser},processing/{chunker,cleaner},registry,safety,cli}.py` + `config/sources.yaml` (5 sources, weekly CN 02:00 Asia/Ho_Chi_Minh `docs/rag_pipeline.md:35`, Qdrant alias `finsight_knowledge` blue/green `rag_pipeline.md:40`)
- **DB/Auth:** `src/infrastructure/db/{base,models/user,seed}.py`, `src/infrastructure/auth/{jwt,password,dependencies}.py`, `alembic/` migrations
- **MCP:** `src/mcp_server/tools/` + `src/infrastructure/mcp/loader.py` (`load_mcp_tools_sync()` fallible `agent.py:69`)

### 4) Interfaces Layer — 60 nodes `layer:interfaces:60`
**Purpose:** Delivery. HTTP and CLI.
**Key files:**
- `src/interfaces/api/app.py:147` lifespan: `init_deps → init_db → seed_admin/demo → StockAgent() → GuardrailPipeline() → start_scheduler` `app.py:147-199`; middlewares `RequestBodySizeMiddleware` 1MB `app.py:29`, `SecurityHeadersMiddleware`, `CORSMiddleware` (`ALLOWED_ORIGINS`); `api_router` `/api/v1/{ask-stream,auth,memory,traces,rag,market}` `app.py:523-528`; global IP limiter 60/60s `app.py:43`; per-user guardrail rate limit `app.py:355`
- `src/interfaces/api/routes/{auth,market,memory,rag,traces}.py`
- `src/interfaces/cli/console.py`
- `frontend/` (Next.js stub: `frontend/src/`, `components.json`, `tsconfig.json`)

### 5) Shared Kernel — 42 nodes `layer:shared:42`
**Purpose:** Cross-cutting ports/utils, strict DI.
**Key files:**
- `src/shared/base_service.py`, `src/shared/price_data.py`, `src/shared/utils/{time_processor,calculations,env_helpers,cache_keys}.py`
- `src/shared/ports/{cache_port,market_data_port}.py`
- `src/mcp_server/` tools registration, `src/infrastructure/dependencies.py`
- `scripts/` helpers

### 6) Configuration & Deployment — 20 nodes `layer:configuration:20`
**Key files:**
- `pyproject.toml`, `.env.example`, `alembic.ini`, `langgraph.json`, `Dockerfile` (multi-stage 19 lines), `docker-compose.yml`/`docker-compose.dev.yml` (183/186 lines), `.github/workflows/ci.yml` (65 lines), `.pre-commit-config.yaml`

### 7) Testing Suite — 80 nodes `layer:testing:80`
**Purpose:** Unit, integration, spec_drift, eval harness.
**Key files:**
- `src/tests/unit/{test_tool_registry,test_hybrid_splitter,test_market_services,test_financial_services,test_cache_*,test_circuit_breaker,test_guardrail_pipeline,test_output_guardrails,test_llm_provider,test_memory_*}.py` (22 unit files `README.md:205-221`)
- `src/tests/integration/{test_agent_e2e,test_api_endpoints,test_enhanced_agent,test_full_system}.py`
- `src/tests/spec_drift/` schema validation
- `evals/{golden/golden_dataset.jsonl (36 cases),run_benchmark,run_ragas_eval,scripts/build_golden_dataset}.py` — metrics `citation_rate`, `numeric_match_rate`, `faithfulness`

### 8) Documentation — 20 nodes `layer:documentation:20`
**Key files:**
- `README.md` (346 lines) — pain-point evidence, 12 tools table `README.md:83-98`, mermaid workflow `README.md:159-177`, `docs/` (`docs/rag_pipeline.md:60`, `docs/mcp.md`, `docs/observability.md`, `docs/query_specs/*.md` 12 specs)

---

## Key Concepts

**ReAct with explicit handoff:** `reason_node` sets `next_tool_call`; `_should_continue` routes `continue→action→reason` else `final_answer` `agent.py:122-129`. Prevents drift; LLM never called directly from `ToolNode`. `MAX_ITERATIONS=10` `agent.py:47`, `AGENT_TIMEOUT_SECONDS=120` `agent.py:48`.

**Hybrid split → parallel fan-out:** `agent.py:469` `_prepare_and_split` builds memory context (`search_memory` top_k 3) then `HybridQuerySplitter.split()`; single-query path streams tokens via `app.stream(stream_mode="messages")` `agent.py:670`, multi-query `run_queries_parallel` + `ResponseSynthesizer.synthesize` then `apply_output_guardrails` `agent.py:560-572`.

**Prompt caching hygiene:** 3 SystemMessages — static `agent_system` (~213t cacheable), dynamic `Current date: ...` + `memory_context`, temporal per-ticker `end_date` `agent.py:192-224`. Never mixes volatile date into cacheable prefix.

**Port/Adapter DI:** `BaseService(logger_name, CachePort, MarketDataPort?)` `base_service.py:23`; `_cached_fetch` `base_service.py:99` with `make_cache_key`; `for_each_ticker` `base_service.py:28` (ThreadPoolExecutor 5/16, overall timeout capped 120s). No direct `vnstock` import in services.

**Defense in depth:** Input `GuardrailPipeline` 5 guards `pipeline.py:16-22` fail-closed exception `pipeline.py:30-41`; global IP limiter for non-guardrail paths `app.py:304-306` de-duped via `_GUARDRAIL_PATHS` `app.py:242`; output guardrails `output_guardrails.py`, TT135 `rag/safety.py`, `FactVerifier` `fact_verifier.py:13` (confidence 0.8, warning `⚠️` + `📊 Độ tin cậy` `agent.py:436-444`). PII redaction, injection/XSS filters `content_filter.py`, `query_validator.py`.

**RAG weekly full replace:** `sources.yaml` priorities 1-5 (VBPL 24/VBHN-VPQH pdf, TT96/135 pdf/html, HNX/HOSE html_crawl, SSI, CFA/SEC disabled) → ingestion `connectors.py`/`crawler.py` (1.5s delay, robots.txt) → `cleaner → chunker 700/80` → `embedder.py` (OpenAI `text-embedding-3-small` primary, `sentence-transformers` fallback) → Qdrant `finsight_knowledge_YYYYwWW` alias `swap_alias` `rag/pipeline.py:124` + `cleanup_old_backups(7)` `pipeline.py:127`; alias `finsight_knowledge` → `search_knowledge` tool `mcp_server/tools/knowledge.py`.

**Observability first:** `request_id_var` ContextVar threaded through all nodes `agent.py:504`, `TracingCallbackHandler` `agent.py:507`, `get_logger("agent.*")` structured JSON, `get_metrics_collector().record_request_metrics` `app.py:310-314`.

---

## Guided Tour

> 8 steps from `\.ua/knowledge-graph.json:tour` — start from README, walk the request path, end at domain/tests.

| Order | Title | Description | NodeIds |
|-------|-------|-------------|---------|
| 1 | **Project Overview and Documentation** | Start with README and docs to understand pain-point evidence, 12 query types and cited-education positioning. | `document:README.md`, `document:docs/rag_pipeline.md`, `document:docs/observability.md` |
| 2 | **Application Entry Point and HTTP Layer** | Explore FastAPI lifespan, SSE streaming, guardrails and middleware — where HTTP enters. | `file:src/interfaces/api/app.py`, `file:src/interfaces/cli/console.py`, `config:pyproject.toml` |
| 3 | **Core Agent Orchestration (ReAct Loop)** | Deep-dive StockAgent StateGraph (781 lines) with HybridSplitter and SSE threading. | `file:src/application/agents/agent.py`, `file:src/application/agents/hybrid_splitter.py`, `file:src/application/agents/multi_query_runner.py` |
| 4 | **Business Logic Services** | 12 service handlers on BaseService fan-out (price, indicator RSI/SMA, financial ratios…). | `file:src/shared/base_service.py`, `file:src/application/services/market/price_service.py`, `file:src/application/services/market/indicator_service.py`, `file:src/application/services/financial/financial_ratio_service.py` |
| 5 | **Infrastructure: Data, Cache and LLM** | Adapters, vn_stock_client, L1/L2 cache, LLM fallback — the hexagon boundary. | `file:src/infrastructure/api_clients/vn_stock_client.py`, `file:src/infrastructure/adapters/vn_stock_adapter.py`, `file:src/infrastructure/cache/cache_manager.py`, `file:src/infrastructure/llm/llm_provider.py` |
| 6 | **RAG Knowledge Pipeline** | Weekly blue/green pipeline, ingestion rate limiting, embedding fallback, TT135 safety. | `file:src/infrastructure/rag/pipeline.py`, `file:src/infrastructure/rag/vector_store.py`, `file:src/infrastructure/rag/retriever.py`, `document:docs/rag_pipeline.md` |
| 7 | **Reliability and Observability** | Guardrails, circuit breaker, request_id tracing, metrics, LangChain tracing handler. | `file:src/infrastructure/guardrails/pipeline.py`, `file:src/infrastructure/resilience/circuit_breaker.py`, `file:src/infrastructure/observability/tracing/tracer.py`, `file:src/infrastructure/observability/logging/logger.py` |
| 8 | **Domain and Testing** | Domain ubiquitous language and the test/eval harness (golden 36, RAGAS). | `file:src/domain/schemas/price.py`, `file:src/domain/entities/time_range.py`, `file:src/tests/integration/test_agent_e2e_pipeline.py` |

**Learning path:** Run the agent once (`src/application/agents/agent.py:608` `run()` → `run_stream()`), then trace `ask_stock_agent_stream` `app.py:385` → `agent.py:701` → `services/*` → `adapters/*`.

---

## File Map (organized by layer)

> Summaries from graph nodes; file paths are `id` values (prefix indicates type: `file:`, `config:`, `document:`, `service:`, `pipeline:`).

### Domain Layer `src/domain/`
- `file:src/domain/entities/time_range.py` — Domain value objects `HistoricalQuery`, `Interval`, `RequestedField`
- `file:src/domain/schemas/price.py` — 12 Pydantic query schemas
- `file:src/domain/{__init__,entities/__init__,schemas/__init__}.py` — package barrels

### Application Layer `src/application/`
- `file:src/application/agents/agent.py` — Core ReAct agent (see above)
- `file:src/application/agents/hybrid_splitter.py` — multi-intent splitter
- `file:src/application/agents/custom_tool_node.py` — ToolNode with history/cache/retries
- `file:src/application/agents/fact_verifier.py` — citation verifier 0.8
- `file:src/application/agents/multi_query_runner.py` — parallel runner
- `file:src/application/agents/response_synthesizer.py` — merge synthesizer
- `file:src/application/prompts/registry.py` + `config:src/application/prompts/templates/{agent_system,query_splitter,response_synthesis}.yaml` — prompt registry
- `file:src/application/services/market/{price,indicator,compare,ranking,forecast,alert,sector}_service.py` — market handlers
- `file:src/application/services/financial/{aggregate,financial_ratio,ranking}_service.py` — financial handlers
- `file:src/application/services/company/company_service.py` — company metadata
- `file:src/application/services/portfolio/{portfolio,news_sentiment}_service.py` — portfolio & sentiment

### Infrastructure Layer `src/infrastructure/`
- `file:src/infrastructure/api_clients/vn_stock_client.py` — vnstock SDK wrapper
- `file:src/infrastructure/adapters/*.py` (6 files) — port implementations
- `file:src/infrastructure/cache/{cache_manager,memory_cache,redis_cache,cache_keys,serialization,session_manager,config}.py` — two-tier cache
- `file:src/infrastructure/llm/llm_provider.py` — LLM fallback
- `file:src/infrastructure/guardrails/{pipeline,content_filter,query_validator,rate_limiter,tickers,output_guardrails}.py` — guardrails
- `file:src/infrastructure/memory/{memory_manager,short_term/memory}.py` — short/episodic memory
- `file:src/infrastructure/observability/{logging/logger,tracing/*,metrics/collector,alerting/manager}.py` — observability
- `file:src/infrastructure/rag/{pipeline,vector_store,retriever,embedder,safety,scheduler,registry,ingestion/*,processing/*,cli}.py` — RAG
- `file:src/infrastructure/{auth/*,db/*,dependencies,mcp/loader,resilience/circuit_breaker}.py`
- `config:src/infrastructure/rag/config/sources.yaml` — RAG sources config

### Interfaces Layer `src/interfaces/` + `frontend/`
- `file:src/interfaces/api/app.py` — FastAPI app (see above)
- `file:src/interfaces/api/routes/{auth,market,memory,rag,traces}.py`
- `file:src/interfaces/cli/console.py` — CLI
- `frontend/*` — Next.js stub (`frontend/src/`, `components.json`, `tsconfig.json`, `eslint.config.mjs`)

### Shared Kernel `src/shared/` + `src/mcp_server/` + `scripts/`
- `file:src/shared/base_service.py` — BaseService fan-out
- `file:src/shared/utils/{time_processor,calculations,env_helpers}.py`
- `file:src/shared/ports/{cache_port,market_data_port}.py`
- `file:src/mcp_server/tools/*.py` — 12 tool definitions consumed via loader
- `file:scripts/load_with_polars.py` — script helper

### Configuration & Deployment
- `config:pyproject.toml`, `config:.env.example`, `config:alembic.ini`, `config:langgraph.json` — configs
- `service:Dockerfile`, `service:docker-compose.yml`, `service:docker-compose.dev.yml` — container orchestration
- `pipeline:.github/workflows/ci.yml` — CI

### Testing Suite `src/tests/` + `evals/`
- `file:src/tests/unit/**/*` (22 unit files covering tool registry, hybrid splitter, market/financial/portfolio services, base_service, cache, circuit breaker, guardrails, LLM provider, memory, domain, calculations, time_processor)
- `file:src/tests/integration/{test_agent_e2e,test_api_endpoints,test_enhanced_agent,test_full_system}.py`
- `file:evals/{run_benchmark,run_ragas_eval,scripts/build_golden_dataset}.py` + `evals/golden/golden_dataset.jsonl` + `evals/baselines/baseline-v1.json`

### Documentation `docs/` + `README.md`
- `document:README.md` — overview, pain-point evidence, 12 tools, mermaid workflow
- `document:docs/{mcp,observability,rag_pipeline}.md`
- `document:docs/query_specs/*.md` (12 specs: price, indicator, company, comparison, ranking, financial_ratio, forecast, portfolio, news_sentiment, alert, sector, aggregate)
- `document:AGENTS.md`, `document:frontend/README.md`, `document:evals/README.md`

---

## Complexity Hotspots

> 34 nodes with `complexity=complex` (>200 non-empty lines). Approach carefully; high fan-out, statefulness or external I/O.

| File | Why complex | Tags | What to watch |
|------|-------------|------|---------------|
| `src/application/agents/agent.py:781` | ReAct loop, dual sync/stream, threading SSE bridge `agent.py:416`, deadline/event-limit guards `agent.py:525` | `agent`, `react`, `tested` | Infinite-loop risk, lost request_id across threads, LLM tool-schema drift |
| `src/interfaces/api/app.py:528` | 3 middlewares + trace + IP vs per-user rate limit dedup `app.py:304`, SSE queue 64 `app.py:416` | `api-handler`, `http` | Concurrency, body-size vs guardrail path, `_ip_request_counts` unbounded (cap 100k) |
| `src/infrastructure/rag/pipeline.py:137` | 6-step full replace + alias swap `pipeline.py:124` + 7-day backup | `rag` | Orphan collections on failure, embedding fallback race |
| `src/infrastructure/llm/llm_provider.py:275` | OpenAI/Groq fallback, tool binding, circuit breaker | `llm`, `tested` | API key rotation, tool schema version skew |
| `src/infrastructure/guardrails/{content_filter,query_validator,output_guardrails}.py` ~200-300 lines | Injection/PII/XSS regex chains | `guardrail`, `tested` | Over-blocking Vietnamese queries, regex ReDoS |
| `src/infrastructure/cache/{cache_manager,redis_cache,memory_cache,config,session_manager}.py` | Two-tier coherence, TTL, serialization `msgpack`, session GC | `caching`, `tested` | Redis failover, L1/L2 inconsistency, msgpack version |
| `src/infrastructure/observability/{tracing/tracer,storage,langchain_handler,logging/logger,metrics/collector}.py` 250-330 lines | Span lifecycle, ContextVar propagation `agent.py:504` | `observability` | Lost traces in `run_in_executor`, cardinality explosion |
| `src/application/services/market/indicator_service.py` | SMA/RSI via vnstock + TA-lib fallback | `service` | NaN handling `base_service.py:84`, interval detection `calculations.py` |
| `src/application/services/financial/financial_ratio_service.py` | PE etc. with period handling | `service` | Period mapping, stale financials |
| `src/application/services/portfolio/{portfolio,news_sentiment}_service.py` | Portfolio calc + sentiment aggregation | `service` | News rate limiting, portfolio JSON schema `user_portfolio_default.json` |
| `README.md:346` | Long documentation (346 lines) | `documentation` | Keep onboarding sync after architecture changes |

**Safer areas to start:** `src/domain/` (pure), `src/shared/utils/time_processor.py:146`, `src/application/services/market/price_service.py` (thin wrapper).

---

## Knowledge Graph Stats

- **Files scanned:** 331 (`config 13`, `infra 5`, `code 292`, `docs 20`, `markup 1`) — filtered 0.
- **Languages:** python 240, typescript 46, markdown 20, yaml 8, json 5, javascript 2, dockerfile 2, css 1, toml 1, etc.
- **Nodes:** 1278 (`file 293`, `function 777`, `class 165`, `service 9`, `pipeline 1`, `config 13`, `document 20`)
- **Edges:** 2370 (`contains 947`, `exports 939`, `imports 428`, `tested_by 53`, `deploys 1`, `documents 1`, `configures 1`) — cross-batch via `neighborMap`/`batchImportData`.
- **Layers:** 8 (above); **Tour:** 8 steps; **Review issues:** 0 (warnings: 78 orphans — expected for docs/config/__init__).
- **Fingerprints:** `\.ua/fingerprints.json` (331 files) for incremental updates.

**Freshness:** Graph at `bada90f` (HEAD). If `git diff --name-only HEAD` shows source changes, re-run `/understand` (or `/understand --full`) then `/understand-onboard` to regenerate this doc.

**Dashboard:** After graph generation, run `/understand-dashboard` to launch interactive exploration (layers, tour, hotspots). Graph file: `\.ua/knowledge-graph.json` (1221038 bytes), `\.ua/meta.json` (`analyzedAt 2026-09-09T10:46:58+07:00`, `gitCommitHash bada90f`).

---

## Next Steps for New Contributors

1. **Read tour step 1-3** then `src/application/agents/agent.py:250` `reason_node` → `action_node` → `final_answer_node`.
2. **Pick one service** (e.g., `price_service.py`) and trace `BaseService.for_each_ticker` → `vn_stock_adapter.py` → `vn_stock_client.py`.
3. **Add a test** under `src/tests/unit/` following existing `test_market_services.py` pattern; ensure `tested_by` edge appears in next graph.
4. **Run evals:** `python evals/run_benchmark.py` and check `citation_rate` before submitting PR.

> **Save location:** This guide lives at `docs/UA_ONBOARDING.md`. Suggest committing it so the team shares the same entry point; keep `\.ua/` gitignored (generated artifacts).

