# Evals — Golden Dataset, RAGAS & Benchmark

## Cấu trúc

```
evals/
├── golden/golden_dataset.jsonl     # 36 cases phủ 12 query types + compound + edge
├── baselines/baseline-v1.json      # baseline regression đã pin
├── scripts/
│   ├── build_golden_dataset.py     # snapshot ground truth bằng tool thật (vnstock)
│   ├── validate_golden_dataset.py  # kiểm schema, ticker, tool names
│   └── recover_samples_from_traces.py
├── run_ragas_eval.py               # runner RAGAS thuần
├── run_benchmark.py                # benchmark đầy đủ: RAGAS + deterministic metrics
├── compare_reports.py              # diff 2 report → phát hiện regression
└── reports/<run_id>/               # report.{json,md} + samples_full.json
```

## Golden dataset

Mỗi case:

```json
{
  "id": "price_001",
  "query_type": "price",
  "query": "Giá đóng cửa của VCB ngày 28/06/2024 là bao nhiêu?",
  "ground_truth": {"close_vcb": 56.11},
  "expected_tools": ["get_stock_price"],
  "as_of_date": "2024-06-28",
  "difficulty": "easy",
  "notes": ""
}
```

- **Chiến lược fixed-date**: câu hỏi neo mốc lịch → ground truth ổn định.
- Ground truth do `build_golden_dataset.py` sinh bằng cách gọi **service handler thật** (cùng code path với agent), không bịa số.
- Case realtime (`price_005`) và forecast/news chỉ chấm faithfulness/format, không so số tuyệt đối.
- Case ratio đang `needs_snapshot: true` do endpoint VCI của vnstock hỏng upstream.

Cập nhật ground truth:

```bash
python evals/scripts/validate_golden_dataset.py      # luôn chạy trước khi commit
python evals/scripts/build_golden_dataset.py         # fill các case còn null
```

## Chạy evaluation

```bash
# Smoke (không tốn judge LLM): chỉ chạy agent, lưu contexts/responses
python evals/run_ragas_eval.py --ids price_001 --skip-ragas

# Chạy subset có chấm điểm RAGAS (judge = gpt-4o-mini, key từ .env)
python evals/run_ragas_eval.py --ids price_001 price_002 ind_001

# Chạy toàn bộ dataset
python evals/run_ragas_eval.py
```

## Benchmark đầy đủ + baseline regression

```bash
# Full benchmark: 36 cases × (RAGAS judge + deterministic metrics) ~30-45'
python evals/run_benchmark.py --pin-baseline

# Chỉ deterministic (không tốn judge): tool accuracy, citation, numeric, latency
python evals/run_benchmark.py --skip-ragas

# Re-score samples đã chạy (không gọi lại agent) — dùng khi sửa GT/metric
python evals/run_benchmark.py --samples-from <run_dir>/samples_full.json

# Resume sau khi gián đoạn
python evals/run_benchmark.py --resume-from <run_dir>/partial.json
```

Deterministic metrics (tính từ trace store, chi phí 0):
- `tool_precision/recall` — so `expected_tools` với tool spans trong trace
- `citation_rate` — tỷ lệ answer có citation `[TICKER: …, nguồn: …]`
- `numeric_match_rate` — số liệu trong answer khớp ground truth (±0.5%, hiểu cả "32,71" lẫn "12,379,504")
- `edge_pass_rate` — case biên: không bịa số / có xin làm rõ
- `latency_p50/p95`, `tokens/case`

### Regression gate

```bash
python evals/compare_reports.py evals/baselines/baseline-v1.json evals/reports/<run>/report.json
# exit 1 nếu metric tụt > 2% → fail CI
```

Metrics: `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall` (case có reference).

Contexts lấy trực tiếp từ **tool spans trong trace store** — mỗi report gắn kèm trace_id để debug từng case.

## So sánh / regression gate

```bash
python evals/compare_reports.py evals/reports/<baseline> evals/reports/<candidate> --threshold 0.02
```

Exit code 1 nếu bất kỳ metric nào tụt quá ngưỡng → dùng làm gate CI khi đổi prompt version.

## Chi phí

~36 cases × (agent loop ≈ 3-5 LLM calls + 4 judge calls) ≈ vài trăm nghìn token/run với gpt-4o-mini. Dùng `--limit`/`--ids` để kiểm soát.
