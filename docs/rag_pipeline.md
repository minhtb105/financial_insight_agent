# RAG Data Pipeline — Weekly Full Replace

> Tự động theo dõi, tải, thay thế toàn bộ dữ liệu RAG (kể cả embedding) 1 tuần/lần — CN 02:00 Asia/Ho_Chi_Minh, giữ 1 bản backup 7 ngày. Lớp `vnstock` live không đưa vào pipeline.

## Nguồn

| Priority | Nguồn | Type |
|----------|-------|------|
| 1 | VBPL 24/VBHN-VPQH (Luật CK hợp nhất) | pdf |
| 2 | TT 96/2020, TT 135/2025 | pdf/html |
| 3 | HNX/HOSE docs | html_crawl |
| 4 | SSI Trung tâm kiến thức | html_crawl |
| 5 | CFA/SEC (tắt mặc định) | html_crawl |

Cấu hình: `src/infrastructure/rag/config/sources.yaml`

## Kiến trúc

`ingestion (rate-limit 0.5s, respect robots, no login)` → `cleaner → chunker (700/80)` → `embedder (OpenAI text-embedding-3-small primary, sentence-transformers fallback)` → Qdrant `finsight_knowledge` alias blue/green → `search_knowledge` tool → Agent + TT135 safety.

## Qdrant 3 mode — cấu hình trong `src/infrastructure/rag/vector_store.py:_client()`

| Mode | Env | Khi nào dùng | Ví dụ |
|------|-----|--------------|-------|
| **Embedded (local dev, không cần Docker)** | `QDRANT_PATH=./data/qdrant_local` | Dev trên Windows không có Docker, hoặc Cloud bị chặn firewall | `QDRANT_PATH=./data/qdrant_local` (đã set trong `.env`) |
| **Cloud** | `QDRANT_URL=https://<cluster>.qdrant.io` + `QDRANT_API_KEY` | Prod, network mở | `QDRANT_URL=https://49c11bc4-...cloud.qdrant.io` |
| **Docker** | `QDRANT_HOST=qdrant` + `QDRANT_PORT=6333` | `docker-compose` local | `QDRANT_HOST=qdrant` (mặc định `docker-compose.yml`) |

Priority: `QDRANT_PATH` > `QDRANT_URL` > `QDRANT_HOST`/`PORT`. Thêm `QDRANT_FORCE_LOCAL=true` để ép bỏ qua Cloud khi debug.

## Chạy

```bash
# manual — Windows host (khuyến nghị, dùng .venv Windows)
$env:PYTHONPATH="src"; python -m infrastructure.rag.cli run --force
$env:PYTHONPATH="src"; python -m infrastructure.rag.cli status
$env:PYTHONPATH="src"; python -m infrastructure.rag.cli diff --week 2026w40

# manual — từ WSL dùng Windows python.exe (không cần cài venv trong WSL)
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/f/financial_insight_agent && /mnt/f/miniconda3/python.exe -m infrastructure.rag.cli run --force"
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/f/financial_insight_agent && /mnt/f/miniconda3/python.exe -m infrastructure.rag.cli status"

# alternative — WSL native venv (cần cài deps riêng)
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/f/financial_insight_agent && pip install -e . && PYTHONPATH=src python3 -m infrastructure.rag.cli run --force"

# API (cần ADMIN_API_KEY nếu đã set)
curl -H "X-Admin-Token: $ADMIN_API_KEY" http://localhost:8000/api/v1/admin/rag/status
curl -X POST -H "X-Admin-Token: $ADMIN_API_KEY" -H "Content-Type: application/json" -d '{"force":true}' http://localhost:8000/api/v1/admin/rag/refresh
```

## Scheduler

Backend `src/infrastructure/rag/scheduler.py` dùng APScheduler `CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=Asia/Ho_Chi_Minh)`. Bật bằng `ENABLE_RAG_SCHEDULER=true` (đã set trong `.env` và `docker-compose.yml`).

## Qdrant

- Alias `finsight_knowledge` → collection `finsight_knowledge_YYYYwWW`
- Full replace: tạo collection mới → upsert → `swap_alias` → `cleanup_old_backups(7)`
- Dữ liệu lưu: `data/rag/raw/<source>/<file>`, `data/rag/processed/<week>.jsonl`, `data/rag/manifests/<week>.json`, `data/rag/registry.db`, `data/qdrant_local/` (khi dùng embedded)
- Kiểm tra: `curl http://localhost:6333/collections` (Docker) hoặc `$env:QDRANT_PATH="./data/qdrant_local"; python -c "from infrastructure.rag.vector_store import _client; print(_client().get_collections())"` (embedded)

## Agent tích hợp

- Tool `search_knowledge` trong `src/mcp_server/tools/knowledge.py:search_knowledge` → `src/infrastructure/rag/retriever.py` + `src/infrastructure/adapters/knowledge_adapter.py` (trước đây `src/application/agents/tool_registry.py` đã xóa ở 76556d2)
- Prompt `agent_system` v1.1 (`src/application/prompts/templates/agent_system.yaml`) bổ sung quy tắc citation `[Nguồn: ...]` và safety TT135
- Safety `src/infrastructure/rag/safety.py` lọc khuyến nghị mua/bán cụ thể và thêm disclaimer

## Cài đặt

```bash
pip install -e .  # cài thêm qdrant-client, apscheduler, beautifulsoup4, html2text, pymupdf, pdfminer.six, langchain-text-splitters
```

## Lưu ý

- Crawl tuân thủ `robots.txt` (hiện `respect_robots=false` + `delay 0.5s` cho dev, prod giữ `true`/`1.5s`), không đăng nhập, `verify=False` cho `hnx.vn`/`vbpl.vn` self-signed
- Seed fallback trong `src/infrastructure/rag/ingestion/connectors.py:SEED_TEXTS` cho `vbpl.vn` timeout, `thuvienphapluat.vn` 403 Cloudflare, `hsx.vn` SPA
- Embedding fallback tự động nếu `OPENAI_API_KEY` thiếu hoặc lỗi → `intfloat/multilingual-e5-base` 768 (cần `load_dotenv` trong `embedder.py`/`vector_store.py`)
- Backup giữ 7 ngày, xóa tự động sau swap; với embedded, alias vẫn hoạt động qua `get_aliases()` local

## WSL integration

- WSL gọi Windows Python để tái dùng `.venv` Windows, tránh cài venv riêng trong WSL: `/mnt/f/miniconda3/python.exe -m ...` (hoặc `/mnt/c/Users/DELL/...` tùy cài đặt)
- Docker trong WSL cần `systemctl start docker` trước khi `docker compose -f docker-compose.dev.yml up -d qdrant`; nhưng với `QDRANT_PATH` embedded thì không cần Docker.
