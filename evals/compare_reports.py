"""Compare two RAGAS eval reports to detect regressions (e.g., prompt changes).

Usage::

    python evals/compare_reports.py evals/reports/<runA> evals/reports/<runB>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_aggregate(path: Path) -> dict:
    if path.is_dir():
        path = path / "report.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "aggregate" in payload and "samples" not in payload:
        return payload["aggregate"]  # compare_reports-style report or baseline
    return payload.get("aggregate", {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("--threshold", type=float, default=0.02,
                        help="relative drop considered a regression")
    args = parser.parse_args()

    base = load_aggregate(Path(args.baseline))
    cand = load_aggregate(Path(args.candidate))
    if not base or not cand:
        print("ERROR: could not locate aggregate in one of the inputs.")
        return 2

    print(f"{'metric':<22} {'baseline':>10} {'candidate':>10} {'delta':>9}  verdict")
    regressions = []
    for metric in sorted(set(base) | set(cand)):
        b, c = base.get(metric), cand.get(metric)
        if b is None or c is None:
            print(f"{metric:<22} {b!s:>10} {c!s:>10} {'—':>9}  (missing)")
            continue
        delta = round(c - b, 4)
        rel = (c - b) / b if b else 0
        if rel < -args.threshold:
            verdict = "REGRESSION"
            regressions.append(metric)
        elif rel > args.threshold:
            verdict = "improved"
        else:
            verdict = "~"
        print(f"{metric:<22} {b:>10.4f} {c:>10.4f} {delta:>+9.4f}  {verdict}")

    if regressions:
        print(f"\nFAILED: {len(regressions)} metric(s) regressed beyond "
              f"{args.threshold:.0%}: {', '.join(regressions)}")
        return 1
    print("\nOK: no regression detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
