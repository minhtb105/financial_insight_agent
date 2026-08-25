"""Full benchmark for the financial insight agent over the golden dataset.

Combines two metric families into one report (and one regression baseline):

1. RAGAS quality metrics   — faithfulness, answer relevancy, context
   precision/recall (judge = OpenAI gpt-4o-mini, key from .env).
2. Deterministic metrics   — computed from traces and responses at zero LLM
   cost: tool-selection precision/recall vs ``expected_tools``, citation-format
   rate, numeric ground-truth match (fixed-date cases), edge-case behavior,
   latency percentiles, tokens per case.

The merged ``aggregate`` dict is directly comparable via
``evals/compare_reports.py``.

Usage::

    python evals/run_benchmark.py                 # full 36-case run + judge
    python evals/run_benchmark.py --limit 3       # smoke
    python evals/run_benchmark.py --skip-ragas    # deterministic metrics only
    python evals/run_benchmark.py --pin-baseline  # also write baselines/baseline-v1.json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from run_ragas_eval import (  # noqa: E402
    DEFAULT_DATASET,
    REPORTS_DIR,
    load_cases,
    run_case,
    score_samples,
)

BASELINES_DIR = ROOT / "evals" / "baselines"
BASELINE_NAME = "baseline-v1.json"

_NUMERIC_TOLERANCE = 0.005  # ±0.5%
_GT_SKIP_KEYS = {"needs_snapshot", "error", "behavior", "snapshot"}


# ---------------------------------------------------------------------------
# Deterministic helpers (pure functions — unit-testable without LLM)
# ---------------------------------------------------------------------------


def extract_numbers(text: str) -> list[float]:
    """Pull plausible numbers out of a Vietnamese answer.

    Handles thousands separators ("12,379,504"), decimal dot ("56.11") and
    Vietnamese decimal comma ("32,71").
    """
    out: list[float] = []
    for raw in re.findall(r"\d+(?:[.,]\d+)*", text or ""):
        is_thousands = bool(re.match(r"^\d{1,3}(,\d{3})+$", raw))
        with contextlib.suppress(ValueError):
            out.append(float(raw.replace(",", "") if is_thousands else raw))
        if "," in raw and not is_thousands:
            with contextlib.suppress(ValueError):  # 32,71 → 32.71
                out.append(float(raw.replace(",", ".")))
    return out


def numeric_match(response: str, ground_truth: dict) -> bool | None:
    """True if every numeric GT value appears in the response within tolerance."""
    targets = [
        float(v) for k, v in ground_truth.items()
        if isinstance(v, (int, float)) and v is not None and k not in _GT_SKIP_KEYS
    ]
    if not targets:
        return None
    numbers = extract_numbers(response)
    if not numbers:
        return False
    for target in targets:
        tol = max(abs(target) * _NUMERIC_TOLERANCE, 1e-9)
        if not any(abs(n - target) <= tol for n in numbers):
            return False
    return True


def tool_precision_recall(actual: set[str], expected: set[str]) -> tuple[float | None, float | None]:
    if not expected:
        return None, None
    tp = len(actual & expected)
    precision = tp / len(actual) if actual else 0.0
    recall = tp / len(expected)
    return precision, recall


_CITATION_RE = re.compile(
    r"\[[A-Z]{2,4}\s*:\s*[\d.,]+[^]]*ngu[oôồốổỗộ][^]]*\]", re.IGNORECASE
)


def has_citation(response: str) -> bool:
    return bool(_CITATION_RE.search(response or ""))


_CLARIFY_RE = re.compile(
    r"\?|làm rõ|cho (?:biết|tôi) (?:mã|cổ phiếu)|bạn muốn|mã nào|xác định(?:\s+ticker)?",
    re.IGNORECASE,
)


def edge_behavior_ok(query_type: str, response: str) -> bool | None:
    if query_type == "edge_invalid_ticker":
        lowered = (response or "").lower()
        fabricated = re.search(r"(?:giá|price)[^.\n]{0,60}\b\d[\d.,]*\b", lowered)
        explains_problem = any(
            kw in lowered for kw in ("không", "lỗi", "err", "không tìm thấy", "không hợp lệ")
        )
        return explains_problem and not fabricated
    if query_type == "edge_ambiguous":
        return bool(_CLARIFY_RE.search(response or ""))
    return None


def score_case_deterministic(case: dict, sample: dict, trace_detail: dict | None) -> dict:
    """Compute zero-cost metrics for one case from its sample + trace."""
    response = sample.get("response", "")
    qtype = case["query_type"]
    gt = case.get("ground_truth") or {}

    result: dict[str, object] = {"id": case["id"], "query_type": qtype}

    expected = set(case.get("expected_tools") or [])
    if trace_detail is not None:
        actual = {
            s["name"] for s in trace_detail.get("spans", []) if s.get("kind") == "tool"
        }
    else:
        actual = set()
    precision, recall = tool_precision_recall(actual, expected)
    result["tool_precision"] = precision
    result["tool_recall"] = recall

    result["citation"] = has_citation(response) if response else False

    if isinstance(gt, dict) and gt.get("needs_snapshot"):
        result["numeric_match"] = None
    else:
        result["numeric_match"] = numeric_match(response, gt) if gt else None

    result["edge_ok"] = edge_behavior_ok(qtype, response)

    meta = sample.get("meta", {})
    result["latency_ms"] = meta.get("latency_ms")
    total_tokens = None
    if trace_detail is not None:
        total_tokens = trace_detail.get("total_tokens")
    result["total_tokens"] = total_tokens
    result["trace_id"] = meta.get("trace_id")
    return result


def aggregate_deterministic(rows: list[dict]) -> dict[str, object]:
    def mean_of(key: str) -> float | None:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return round(statistics.mean(vals), 4) if vals else None

    latencies = sorted(r["latency_ms"] for r in rows if isinstance(r.get("latency_ms"), (int, float)))

    def pct(p: float) -> float | None:
        if not latencies:
            return None
        idx = min(len(latencies) - 1, round(p / 100 * (len(latencies) - 1)))
        return latencies[idx]

    citations = [r for r in rows if isinstance(r.get("citation"), bool)]
    edges = [r for r in rows if isinstance(r.get("edge_ok"), bool)]
    numerics = [r for r in rows if isinstance(r.get("numeric_match"), bool)]

    tokens = [
        r["total_tokens"] for r in rows if isinstance(r.get("total_tokens"), (int, float))
    ]
    return {
        "tool_precision": mean_of("tool_precision"),
        "tool_recall": mean_of("tool_recall"),
        "citation_rate": (
            round(sum(1 for r in citations if r["citation"]) / len(citations), 4)
            if citations else None
        ),
        "numeric_match_rate": (
            round(sum(1 for r in numerics if r["numeric_match"]) / len(numerics), 4)
            if numerics else None
        ),
        "edge_pass_rate": (
            round(sum(1 for r in edges if r["edge_ok"]) / len(edges), 4)
            if edges else None
        ),
        "latency_p50_ms": pct(50),
        "latency_p95_ms": pct(95),
        "avg_tokens_per_case": (
            round(statistics.mean(tokens)) if tokens else None
        ),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_RAGAS_KEYS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
_DET_KEYS = (
    "tool_precision", "tool_recall", "citation_rate", "numeric_match_rate",
    "edge_pass_rate", "latency_p50_ms", "latency_p95_ms", "avg_tokens_per_case",
)


def fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}" if abs(value) <= 10 else f"{value:.0f}"
    return str(value)


def write_benchmark_report(run_dir: Path, results: dict, det_rows: list[dict]) -> None:
    agg = results["aggregate"]

    lines = [
        "# Benchmark Report",
        "",
        f"- Run ID: `{results['run_id']}`",
        f"- Judge model: `{results['judge_model']}`",
        f"- Cases scored by RAGAS: {results['n_cases_ragas']}",
        f"- Deterministic rows: {len(det_rows)}",
        "",
        "## Aggregate",
        "",
        "| Metric | Value | Family |",
        "|---|---|---|",
    ]
    for key in _RAGAS_KEYS:
        lines.append(f"| {key} | {fmt(agg.get(key))} | ragas |")
    for key in _DET_KEYS:
        lines.append(f"| {key} | {fmt(agg.get(key))} | deterministic |")

    lines += [
        "",
        "## Per-case (deterministic)",
        "",
        "| Case | Type | ToolP | ToolR | Cite | NumMatch | Edge | Latency ms | Tokens |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in det_rows:
        lines.append(
            f"| {r['id']} | {r['query_type']} | {fmt(_round(r['tool_precision']))} "
            f"| {fmt(_round(r['tool_recall']))} | {fmt(_bool(r['citation']))} "
            f"| {fmt(_tri(r['numeric_match']))} | {fmt(_tri(r['edge_ok']))} "
            f"| {fmt(r['latency_ms'])} | {fmt(r['total_tokens'])} |"
        )
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _round(v):
    return round(v, 3) if isinstance(v, (int, float)) else v


def _bool(v) -> str:
    return "✓" if v is True else "✗" if v is False else "—"


def _tri(v) -> str:
    return "✓" if v is True else "✗" if v is False else "—"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", nargs="*", default=None)
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument("--skip-ragas", action="store_true")
    parser.add_argument("--resume-from", default=None,
                        help="path to partial.json from an interrupted run; "
                             "already-scored case ids are skipped and reused")
    parser.add_argument("--samples-from", default=None,
                        help="path to samples_full.json / report.json containing "
                             "raw samples + det_rows; skips agent execution entirely")
    parser.add_argument("--pin-baseline", action="store_true",
                        help=f"write aggregate to {BASELINES_DIR / BASELINE_NAME}")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    cases_by_id: dict[str, dict] = {}
    if args.samples_from:
        prior = json.loads(Path(args.samples_from).read_text(encoding="utf-8"))
        samples = prior["samples"]
        cases_by_id = {
            c["id"]: c
            for c in load_cases(Path(args.dataset), None, None)
        }
        print(f"[bench] loaded {len(samples)} sample(s) from {args.samples_from} — "
              f"skipping execution; deterministic metrics will be recomputed "
              f"against the CURRENT dataset")
    else:
        cases = load_cases(Path(args.dataset), args.ids, args.limit)

    samples_local: list[dict] | None = None
    det_rows_local: list[dict] | None = None
    done_ids: set[str] = set()
    pending: list[dict] = []
    det_rows: list[dict] = []
    if args.resume_from and not args.samples_from:
        prior = json.loads(Path(args.resume_from).read_text(encoding="utf-8"))
        samples_local = prior.get("samples", [])
        det_rows_local = prior.get("det_rows", [])
        done_ids = {r["id"] for r in det_rows_local}
        print(f"[bench] resuming: {len(done_ids)} case(s) reused from "
              f"{args.resume_from}")

    if not args.samples_from:
        pending = [c for c in (cases or []) if c["id"] not in done_ids]
        if samples_local is not None:
            samples = samples_local
            det_rows = list(det_rows_local or [])
        print(f"[bench] {len(pending)} case(s) to run ({len(done_ids)} reused)")

    from application.agents.agent import StockAgent
    from infrastructure.observability.tracing import get_tracer, init_tracing

    init_tracing()
    tracer = get_tracer()

    if args.samples_from:
        agent = None
        det_rows = []
        for s in samples:
            case = cases_by_id[s["meta"]["id"]]
            tid = s["meta"].get("trace_id")
            td = tracer.store.get_trace(tid) if tid and tracer.store else None
            det_rows.append(score_case_deterministic(case, s, td))
    else:
        agent = StockAgent()
        if agent.llm_provider is None:
            print("[bench] FATAL: LLM unavailable (check OPENAI_API_KEY)")
            return 1

    if args.samples_from:
        base_run = re.sub(r"^(rescore|partial|resume)-", "", str(prior.get("run_id", "")))
        run_id = f"rescore-{base_run or run_id}"
    elif samples:
        run_id = f"partial-{run_id}"
    run_dir = REPORTS_DIR / f"benchmark-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()
    for i, case in enumerate(pending, start=1):
        print(f"[bench] ({i}/{len(pending)}) {case['id']}: {case['query'][:60]}...")
        try:
            sample = run_case(agent, case)
        except Exception as exc:
            print(f"[bench]   FAILED: {type(exc).__name__}: {exc}")
            sample = {
                "user_input": case["query"],
                "response": f"(agent error: {exc})",
                "retrieved_contexts": [],
                "reference": None,
                "meta": {"id": case["id"], "query_type": case["query_type"],
                         "trace_id": None, "latency_ms": None},
            }
        samples.append(sample)

        trace_detail = None
        tid = sample["meta"].get("trace_id")
        if tid and tracer.enabled and tracer.store is not None:
            trace_detail = tracer.store.get_trace(tid)
        det_rows.append(score_case_deterministic(case, sample, trace_detail))

        # incremental dump so long runs never lose progress
        (run_dir / "partial.json").write_text(
            json.dumps({"run_id": run_id, "samples": samples, "det_rows": det_rows},
                       ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    print(f"[bench] execution done in {time.time() - t_start:.0f}s "
          f"({len(samples)} total cases) — scoring...")

    aggregate: dict[str, object] = {}
    n_ragas = 0
    if not args.skip_ragas:
        ragas_results = score_samples(samples, args.judge_model)
        aggregate.update(ragas_results["aggregate"])
        n_ragas = len(samples)

    det_aggregate = aggregate_deterministic(det_rows)
    aggregate.update(det_aggregate)

    results = {
        "run_id": run_id,
        "judge_model": None if args.skip_ragas else args.judge_model,
        "n_cases_ragas": n_ragas,
        "aggregate": aggregate,
        "per_case_ragas": ragas_results.get("per_case", []) if not args.skip_ragas else [],
    }

    (run_dir / "report.json").write_text(
        json.dumps({**results, "samples": samples,
                    "samples_meta": [s["meta"] for s in samples],
                    "det_rows": det_rows},
                   ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    # keep raw samples for later re-scoring without re-running the agent
    partial = run_dir / "partial.json"
    if partial.exists():
        partial.rename(run_dir / "samples_full.json")
    write_benchmark_report(run_dir, results, det_rows)

    print("\n[bench] Aggregate:")
    for key in (*_RAGAS_KEYS, *_DET_KEYS):
        print(f"  {key:<22} {fmt(aggregate.get(key))}")
    print(f"[bench] Report → {run_dir / 'report.md'}")

    if args.pin_baseline:
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        baseline = {
            "pinned_at": run_id,
            "source_report": str(run_dir),
            "aggregate": aggregate,
        }
        (BASELINES_DIR / BASELINE_NAME).write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[bench] Baseline pinned → {BASELINES_DIR / BASELINE_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
