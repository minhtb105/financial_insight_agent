"""Offline eval cho text-to-dashboard — Validity → Legality → Readability trên JSON.

Không cần network (mock _fetch_rows) hay LLM judge: tool là rule-first nên
harness đo đúng chất lượng selector + validator.

Usage::

    python evals/run_dashboard_eval.py               # full 102 cases
    python evals/run_dashboard_eval.py --limit 10    # smoke
    python evals/run_dashboard_eval.py --check       # exit 1 nếu dưới ngưỡng
    python evals/run_dashboard_eval.py --report-out evals/dashboard/v1/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from application.services.dashboard.eval_metrics import (  # noqa: E402
    legality_compare,
    quality_score,
    readability_score,
)
from application.services.dashboard.spec_validator import (  # noqa: E402
    validate_chart_spec,
)

DEFAULT_DATA = ROOT / "evals" / "dashboard" / "v1" / "benchmark.jsonl"

THRESHOLDS = {"validity": 0.90, "chart_type": 0.85, "field": 0.80}

_MOCK_TIMES = [f"2026-03-0{d}" for d in range(1, 6)]
_SINGLE_ROW_TYPES = frozenset({"pie", "donut", "treemap", "heatmap", "scatter"})


def make_rows(symbols: list[str], chart_type: str) -> tuple[list[dict[str, Any]], str]:
    """Dựng rows tổng hợp có đủ mọi cột để validator pass được (đo selector, không đo fetch)."""
    if chart_type in _SINGLE_ROW_TYPES or (chart_type == "bar" and len(symbols) > 1):
        rows = [_row(sym, _MOCK_TIMES[0], 0) for sym in symbols]
    else:
        rows = [_row(sym, t, i) for sym in symbols for i, t in enumerate(_MOCK_TIMES)]
    return rows, f"mock:{','.join(symbols)}"


def _row(sym: str, t: str, i: int) -> dict[str, Any]:
    base = 50.0 + (ord(sym[0]) % 10) + i * 0.7
    return {
        "time": t,
        "symbol": sym,
        "open": round(base - 0.5, 2),
        "high": round(base + 0.8, 2),
        "low": round(base - 0.9, 2),
        "close": round(base, 2),
        "volume": 1_000_000 + i * 50_000,
        "pe": round(12.0 + i * 0.3, 2),
        "roe": round(18.0 + i * 0.2, 2),
        "eps": round(3.0 + i * 0.1, 2),
        "revenue": round(1000.0 + i * 40.0, 2),
        "profit": round(200.0 + i * 12.0, 2),
        "risk": round(0.5 + i * 0.4, 2),
        "return": round(1.0 + i * 0.6, 2),
    }


def load_cases(path: Path, limit: int | None) -> list[dict[str, Any]]:
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases[:limit] if limit else cases


def eval_case(case: dict[str, Any], tool_fn) -> dict[str, Any]:
    if case.get("ask_back"):
        return {"id": case["id"], "ask_back": True, "skipped": "manual agent-level check"}
    symbols = case.get("symbols") or ["VNM"]
    expected = case["expected"]
    rows, source = make_rows(symbols, expected["chart_type"])
    with patch("mcp_server.tools.visualize._fetch_rows", return_value=(rows, source)):
        raw = tool_fn(
            user_request=case["query"],
            chart_type_hint=case.get("hint"),
            symbols=symbols,
            metric=case.get("metric", "close"),
            months=case.get("months", 6),
            days=case.get("days"),
        )
    try:
        payload = json.loads(raw)
        spec = payload.get("spec", {})
    except (json.JSONDecodeError, TypeError, AttributeError):
        return {"id": case["id"], "valid": False, "tool_error": str(raw)[:200]}
    validation = validate_chart_spec(spec)
    leg = legality_compare(spec, expected)
    read = readability_score(spec)
    return {
        "id": case["id"],
        "difficulty": case.get("difficulty"),
        "valid": validation.valid,
        "errors": validation.errors,
        "chart_type_ok": leg.chart_type_ok,
        "x_ok": leg.x_ok,
        "y_ok": leg.y_ok,
        "sort_ok": leg.sort_ok,
        "readability": read.score,
        "readability_failed": read.failed_rules,
        "quality": quality_score(validation.valid, leg, read),
        "got_chart_type": spec.get("chart_type"),
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [r for r in results if not r.get("ask_back") and "valid" in r]
    n = len(scored)
    if n == 0:
        return {"n": 0}
    mean = lambda key: sum(1 for r in scored if r.get(key)) / n
    qualities = [r.get("quality", 0) for r in scored]
    reads = [r.get("readability", 1) for r in scored]
    return {
        "n": n,
        "validity": round(mean("valid"), 4),
        "chart_type_acc": round(mean("chart_type_ok"), 4),
        "x_acc": round(mean("x_ok"), 4),
        "y_acc": round(mean("y_ok"), 4),
        "field_acc": round((mean("x_ok") + mean("y_ok")) / 2, 4),
        "sort_acc": round(mean("sort_ok"), 4),
        "avg_readability": round(sum(reads) / n, 2),
        "avg_quality": round(sum(qualities) / n, 2),
        "quality_ge4_rate": round(sum(1 for q in qualities if q >= 4) / n, 4),
        "ask_back_manual": sum(1 for r in results if r.get("ask_back")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline eval text-to-dashboard")
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--check", action="store_true", help="exit 1 nếu dưới ngưỡng")
    parser.add_argument("--report-out", default=None)
    args = parser.parse_args()

    import mcp_server.tools.visualize as viz
    import mcp_server.tools  # noqa: F401 — ensure registration

    # Static check: description phải hướng dẫn hỏi lại (cho adversarial)
    desc = viz.mcp._tool_manager._tools["generate_chart_spec"].description or ""
    guidance = "hỏi lại" in desc.lower()

    cases = load_cases(Path(args.data), args.limit)
    results = [eval_case(c, viz.generate_chart_spec) for c in cases]

    for r in results:
        if r.get("ask_back") or ("valid" in r and r["valid"] and r.get("chart_type_ok")):
            continue
        print(f"FAIL {r['id']}: valid={r.get('valid')} type={r.get('got_chart_type')} errors={r.get('errors')}")

    summary = summarize(results)
    summary["ask_back_guidance_present"] = guidance
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    verdict_ok = (
        summary.get("validity", 0) >= THRESHOLDS["validity"]
        and summary.get("chart_type_acc", 0) >= THRESHOLDS["chart_type"]
        and summary.get("field_acc", 0) >= THRESHOLDS["field"]
        and guidance
    )
    print(f"VERDICT: {'PASS' if verdict_ok else 'FAIL'} (ngưỡng {THRESHOLDS})")

    if args.report_out:
        report = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "thresholds": THRESHOLDS,
            "summary": summary,
            "verdict": "PASS" if verdict_ok else "FAIL",
            "results": results,
        }
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {out}")

    if args.check and not verdict_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
