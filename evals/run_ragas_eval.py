"""RAGAS evaluation runner for the financial insight agent.

Pipeline:
  1. Load golden dataset (evals/golden/golden_dataset.jsonl)
  2. Run the agent per case with tracing enabled; capture trace_id
  3. Extract retrieved contexts from TOOL spans in the trace store
  4. Score with RAGAS metrics (judge = OpenAI gpt-4o-mini via .env key)
  5. Write report.json + report.md under evals/reports/<run_id>/

Usage::

    python evals/run_ragas_eval.py --limit 3          # smoke run
    python evals/run_ragas_eval.py                    # full dataset
    python evals/run_ragas_eval.py --ids price_001 ind_001 cmp_001
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_DATASET = ROOT / "evals" / "golden" / "golden_dataset.jsonl"
REPORTS_DIR = ROOT / "evals" / "reports"

MAX_CONTEXTS = 10
MAX_CONTEXT_CHARS = 1500


# ---------------------------------------------------------------------------
# Agent execution + context extraction
# ---------------------------------------------------------------------------


def load_cases(dataset: Path, ids: list[str] | None, limit: int | None) -> list[dict]:
    cases = [
        json.loads(ln)
        for ln in dataset.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if ids:
        wanted = set(ids)
        cases = [c for c in cases if c["id"] in wanted]
    if limit:
        cases = cases[:limit]
    return cases


def extract_contexts_from_trace(trace_id: str) -> list[str]:
    """Flatten tool-span outputs of a trace into RAGAS 'retrieved_contexts'."""
    from infrastructure.observability.tracing import get_tracer

    tracer = get_tracer()
    if not tracer.enabled or tracer.store is None:
        return []
    trace = tracer.store.get_trace(trace_id)
    if not trace:
        return []
    contexts: list[str] = []
    for span in trace["spans"]:
        if span.get("kind") != "tool":
            continue
        outputs = span.get("outputs")
        text = outputs if isinstance(outputs, str) else json.dumps(outputs, ensure_ascii=False, default=str)
        if text and text.strip():
            contexts.append(text[:MAX_CONTEXT_CHARS])
        if len(contexts) >= MAX_CONTEXTS:
            break
    return contexts


def run_case(agent, case: dict) -> dict:
    """Execute one golden case; returns sample fields + metadata."""
    t0 = time.time()
    answer = agent.run(case["query"])
    latency_ms = round((time.time() - t0) * 1000, 2)

    # agent.run() resets the contextvar on exit — recover via store lookup by request_id
    from infrastructure.observability.tracing import get_tracer

    tracer = get_tracer()
    trace_id = None
    if tracer.enabled and tracer.store is not None:
        rows = tracer.store.list_traces(limit=5, name_filter="agent.run")
        trace_id = next(
            (r["trace_id"] for r in rows if r.get("request_id")),
            rows[0]["trace_id"] if rows else None,
        )
    contexts = extract_contexts_from_trace(trace_id) if trace_id else []

    return {
        "user_input": case["query"],
        "response": answer,
        "retrieved_contexts": contexts,
        "reference": _reference_text(case),
        "meta": {
            "id": case["id"],
            "query_type": case["query_type"],
            "trace_id": trace_id,
            "latency_ms": latency_ms,
        },
    }


def _reference_text(case: dict) -> str | None:
    gt = case.get("ground_truth")
    if not isinstance(gt, dict):
        return None
    parts = []
    for key, value in sorted(gt.items()):
        if value is None or key == "needs_snapshot":
            continue
        parts.append(f"{key}: {value}")
    return "; ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# RAGAS scoring
# ---------------------------------------------------------------------------


def build_metrics(with_reference: bool) -> list:
    from ragas.metrics import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    metrics = [Faithfulness(), AnswerRelevancy(), ContextPrecision()]
    if with_reference:
        metrics.append(ContextRecall())
    return metrics


def score_samples(samples: list[dict], judge_model: str) -> dict:
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing — cannot run RAGAS judging")

    judge_llm = LangchainLLMWrapper(
        ChatOpenAI(model=judge_model, temperature=0, api_key=api_key, max_retries=3)
    )
    embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model="text-embedding-3-small")
    )

    has_reference = any(s.get("reference") for s in samples)
    flat = []
    for s in samples:
        flat.append({
            "user_input": s["user_input"],
            "response": s["response"],
            "retrieved_contexts": s["retrieved_contexts"] or ["(no tool output captured)"],
            **({"reference": s["reference"]} if s.get("reference") else {}),
        })

    result = evaluate(
        Dataset.from_list(flat),
        metrics=build_metrics(with_reference=has_reference),
        llm=judge_llm,
        embeddings=embeddings,
        raise_exceptions=False,
    )
    df = result.to_pandas()
    score_cols = [c for c in df.columns if c in (
        "faithfulness", "answer_relevancy", "context_precision", "context_recall",
    )]

    def _valid(v) -> bool:
        return isinstance(v, (int, float)) and not (isinstance(v, float) and v != v)

    aggregates = {}
    for col in score_cols:
        values = [v for v in df[col].tolist() if _valid(v)]
        aggregates[col] = round(statistics.mean(values), 4) if values else None

    per_case = df.to_dict(orient="records")
    # NaN (metrics not computable, e.g. missing reference) → None for clean JSON
    for row in per_case:
        for k, v in list(row.items()):
            if isinstance(v, float) and v != v:
                row[k] = None
    return {"aggregate": aggregates, "per_case": per_case}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_report(run_dir: Path, results: dict, samples: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "report.json").write_text(
        json.dumps({**results, "samples_meta": [s["meta"] for s in samples]},
                   ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    agg = results["aggregate"]
    lines = [
        "# RAGAS Evaluation Report",
        "",
        f"- Run ID: `{results['run_id']}`",
        f"- Judge model: `{results['judge_model']}`",
        f"- Cases: {len(samples)}",
        "- Prompt registry dir: `src/application/prompts/templates/`",
        "",
        "## Aggregate scores",
        "",
        "| Metric | Score |",
        "|---|---|",
    ]
    for metric, score in agg.items():
        lines.append(f"| {metric} | {score if score is not None else 'n/a'} |")

    lines += ["", "## Per-case breakdown", "", "| Case | Query type | Latency ms | Faithfulness | Answer relevancy | Trace |", "|---|---|---|---|---|---|"]
    meta_by_id = {m["id"]: m for m in results.get("samples_meta", [])}
    for row in results["per_case"]:
        cid = "?"
        for s in samples:
            if s["user_input"] == row.get("user_input"):
                cid = s["meta"]["id"]
                break
        m = meta_by_id.get(cid, {})
        lines.append(
            f"| {cid} | {m.get('query_type', '')} | {m.get('latency_ms', '')} "
            f"| {_fmt(row.get('faithfulness'))} | {_fmt(row.get('answer_relevancy'))} "
            f"| {m.get('trace_id') or ''} |"
        )
    lines += ["", "## Notes", "",
              "- Ratio cases have `needs_snapshot` ground truth (vnstock VCI endpoint broken upstream); "
              "they are scored on faithfulness/relevancy only.",
              "- Edge cases (invalid ticker / ambiguous query) are graded qualitatively — inspect responses manually."]
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _fmt(value) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", nargs="*", default=None)
    parser.add_argument("--judge-model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--skip-ragas", action="store_true",
                        help="only run the agent and dump contexts/responses (no LLM judge)")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    cases = load_cases(Path(args.dataset), args.ids, args.limit)
    print(f"[eval] {len(cases)} case(s) loaded from {args.dataset}")

    from application.agents.agent import StockAgent
    from infrastructure.observability.tracing import init_tracing

    init_tracing()
    agent = StockAgent()
    if agent.llm_provider is None:
        print("[eval] FATAL: LLM unavailable (check OPENAI_API_KEY)")
        return 1

    samples = []
    for i, case in enumerate(cases, start=1):
        print(f"[eval] ({i}/{len(cases)}) running {case['id']}: {case['query'][:60]}...")
        try:
            samples.append(run_case(agent, case))
        except Exception as exc:
            print(f"[eval]   case FAILED: {type(exc).__name__}: {exc}")
            samples.append({
                "user_input": case["query"], "response": f"(agent error: {exc})",
                "retrieved_contexts": [], "reference": _reference_text(case),
                "meta": {"id": case["id"], "query_type": case["query_type"],
                         "trace_id": None, "latency_ms": None},
            })

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = REPORTS_DIR / run_id

    if args.skip_ragas:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "samples.json").write_text(
            json.dumps(samples, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[eval] skip-ragas: raw samples -> {run_dir / 'samples.json'}")
        return 0

    print("[eval] scoring with RAGAS (this calls the judge LLM per case)...")
    results = score_samples(samples, args.judge_model)
    results["run_id"] = run_id
    results["judge_model"] = args.judge_model

    write_report(run_dir, results, samples)
    print("\n[eval] Aggregate scores:")
    for k, v in results["aggregate"].items():
        print(f"  {k}: {v}")
    print(f"[eval] Report written to {run_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
