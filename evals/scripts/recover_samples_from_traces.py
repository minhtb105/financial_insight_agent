"""One-off: rebuild raw samples from the trace store for re-scoring.

The interrupted-run cleanup deleted partial.json before samples_full.json
existed. Traces are intact, so responses (root span output), tool contexts
(tool span outputs) and token totals can be reconstructed per case.
"""

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from infrastructure.observability.tracing import init_tracing  # noqa: E402
from run_ragas_eval import load_cases, _reference_text  # noqa: E402

tracer = init_tracing()

reports = sorted((ROOT / "evals" / "reports").glob("benchmark-*/report.json"))
report = reports[-1]
data = json.loads(Path(report).read_text(encoding="utf-8"))
det_rows = data["det_rows"]
print("source report:", report)

cases = {c["id"]: c for c in load_cases(ROOT / "evals/golden/golden_dataset.jsonl", None, None)}

samples = []
for row in det_rows:
    cid = row["id"]
    case = cases[cid]
    tid = row.get("trace_id")
    response = ""
    contexts: list[str] = []
    if tid:
        trace = tracer.store.get_trace(tid)
        if trace:
            root = next(
                (s for s in trace["spans"] if s["name"] == "agent.run"), None
            )
            out = (root or {}).get("outputs") or {}
            response = out.get("answer", "") if isinstance(out, dict) else str(out)
            for s in trace["spans"]:
                if s.get("kind") != "tool":
                    continue
                o = s.get("outputs")
                text = o if isinstance(o, str) else json.dumps(o, ensure_ascii=False)
                if text and text.strip():
                    contexts.append(text[:1500])
                if len(contexts) >= 10:
                    break
    samples.append({
        "user_input": case["query"],
        "response": response,
        "retrieved_contexts": contexts,
        "reference": _reference_text(case),
        "meta": {"id": cid, "query_type": case["query_type"],
                 "trace_id": tid, "latency_ms": row.get("latency_ms")},
    })

empty = [s["meta"]["id"] for s in samples if not s["response"]]
print(f"rebuilt {len(samples)} samples; empty responses: {len(empty)} {empty}")

out_path = Path(report).parent / "samples_full.json"
out_path.write_text(
    json.dumps({"run_id": Path(report).parent.name.replace("benchmark-", ""),
                "samples": samples, "det_rows": det_rows},
               ensure_ascii=False, default=str),
    encoding="utf-8",
)
print("written:", out_path)
