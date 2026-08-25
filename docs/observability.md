# Observability: Tracing & Prompt Versioning

## Kiến trúc

```
Request ──► HTTP span (app.py middleware)
             └── agent.run span (StockAgent.run / run_stream)
                   ├── node spans  (reason / action / final_answer / verify_facts)
                   │     └── llm spans (ChatOpenAI — model, tokens, finish)
                   ├── tool spans  (CustomToolNode — args, result, cache/retry status)
                   ├── llm_provider.chain spans (fallback visibility)
                   └── synthesis / splitter llm spans
                          │
                          ▼
              TraceStore (SQLite: data/traces/traces.db)  +  JSONL (opt-in)
```

- Module: `src/infrastructure/observability/tracing/`
  - `models.py` — `Span`, `SpanKind` (agent/node/llm/tool/guardrail/http)
  - `context.py` — ContextVar stack (truyền đúng qua ThreadPoolExecutor của multi-query)
  - `tracer.py` — `Tracer` singleton (`start_span` context manager + manual `begin_span`/`finish_span`)
  - `storage.py` — SQLite (WAL) + JSONL exporter
  - `langchain_handler.py` — callback handler biến LLM run → span có token usage
- Metrics phát thêm vào `MetricsCollector`: `tracing_llm_calls_total`, `tracing_llm_tokens_total{type,model}`, `tracing_tool_calls_total{tool,status}`, histogram latency cho llm/tool.

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `TRACING_ENABLED` | `true` | Bật/tắt toàn bộ tracer |
| `TRACING_DB_PATH` | `data/traces/traces.db` | Đường dẫn SQLite |
| `TRACING_JSONL_ENABLED` | `false` | Ghi mirror JSONL |
| `TRACING_JSONL_PATH` | `data/traces/traces.jsonl` | Đường dẫn JSONL |
| `TRACE_MAX_CONTENT_CHARS` | `2000` | Giới hạn độ dài inputs/outputs mỗi span |

Khởi tạo tự động theo chuỗi: FastAPI lifespan → `init_deps()` → `_init_observability()` → `init_observability()` → `init_tracing()`.

## REST API

- `GET /api/v1/traces?limit=50&offset=0&status=ok&min_duration_ms=100&name_filter=agent`
  — danh sách trace (trace_id, duration, num_spans, total_tokens, llm/tool counts).
- `GET /api/v1/traces/{trace_id}` — span tree đầy đủ.

## Prompt versioning

Templates: `src/application/prompts/templates/*.yaml`

```yaml
name: agent_system
default_version: "1.0"        # pin phiên bản mặc định
versions:
  - version: "1.0"
    status: stable            # stable | draft | deprecated
    template: |
      You are ...
```

Sử dụng:

```python
from application.prompts import get_registry

prompt = get_registry().render("agent_system")               # bản pinned
prompt = get_registry().render("agent_system", version="2.0")
text = get_registry().render("query_splitter").text          # validate placeholder {var}
```

Mỗi lần render tự gắn `prompt_name`/`prompt_version` vào span đang mở → mọi LLM call trong trace đều truy vết được về đúng phiên bản prompt.

### Quy trình tạo prompt v2 (A/B)

1. Thêm entry mới vào YAML (`version: "2.0"`, `status: draft`).
2. Chạy eval trên subset: `python evals/run_ragas_eval.py --ids price_001 ind_001 --limit 5`.
3. So sánh: `python evals/compare_reports.py evals/reports/<runA> evals/reports/<runB>`.
4. Đạt chuẩn → đổi `default_version: "2.0"` và `status: stable`.

## Retention

```python
from infrastructure.observability.tracing import get_tracer
get_tracer().store.purge_older_than(days=30)
```

## Lưu ý đã biết

- vnstock 3.5: endpoint Company VCI hỏng upstream → ratio cases trong golden dataset đánh dấu `needs_snapshot`; service vẫn fail graceful qua `TOOL_ERR#`.
- `VNStockClient` dùng Quote=VCI, Company=KBS do giới hạn nguồn của từng lớp trong vnstock 3.5.
