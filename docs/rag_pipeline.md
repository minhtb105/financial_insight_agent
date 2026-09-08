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

`ingestion (rate-limit 1.5s, respect robots, no login)` → `cleaner → chunker (700/80)` → `embedder (OpenAI text-embedding-3-small primary, sentence-transformers fallback)` → Qdrant `finsight_knowledge` alias blue/green → `search_knowledge` tool → Agent + TT135 safety.

## Chạy

```bash
# manual
python -m infrastructure.rag.cli run --force
python -m infrastructure.rag.cli status
python -m infrastructure.rag.cli diff --week 2026w36

# API (cần ADMIN_API_KEY nếu đã set)
curl -H "X-Admin-Token: $ADMIN_API_KEY" http://localhost:8000/api/v1/admin/rag/status
curl -X POST -H "X-Admin-Token: $ADMIN_API_KEY" -H "Content-Type: application/json" -d '{"force":true}' http://localhost:8000/api/v1/admin/rag/refresh
```

## Scheduler

Backend `src/infrastructure/rag/scheduler.py` dùng APScheduler `CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=Asia/Ho_Chi_Minh)`. Bật bằng `ENABLE_RAG_SCHEDULER=true` (đã set trong `.env` và `docker-compose.yml`).

## Qdrant

- Alias `finsight_knowledge` → collection `finsight_knowledge_YYYYwWW`
- Full replace: tạo collection mới → upsert → `swap_alias` → `cleanup_old_backups(7)`
- Dữ liệu lưu: `data/rag/raw/<source>/<file>`, `data/rag/processed/<week>.jsonl`, `data/rag/manifests/<week>.json`, `data/rag/registry.db`

## Agent tích hợp

- Tool `search_knowledge` trong `src/mcp_server/tools/knowledge.py:search_knowledge` → `src/infrastructure/rag/retriever.py` + `src/infrastructure/adapters/knowledge_adapter.py` (trước đây `src/application/agents/tool_registry.py` đã xóa ở 76556d2)
- Prompt `agent_system` v1.1 (`src/application/prompts/templates/agent_system.yaml`) bổ sung quy tắc citation `[Nguồn: ...]` và safety TT135
- Safety `src/infrastructure/rag/safety.py` lọc khuyến nghị mua/bán cụ thể và thêm disclaimer

## Cài đặt

```bash
pip install -e .  # cài thêm qdrant-client, apscheduler, beautifulsoup4, html2text, pymupdf, pdfminer.six, langchain-text-splitters
```

## Lưu ý

- Crawl tuân thủ `robots.txt`, delay 1.5s, không đăng nhập
- Embedding fallback tự động nếu `OPENAI_API_KEY` thiếu
- Backup giữ 7 ngày, xóa tự động sau swap
