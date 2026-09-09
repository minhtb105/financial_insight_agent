"""Offline golden eval for QueryReformulator (deterministic checks, no judge LLM).

Builds memory inputs directly from each case's history (no Redis needed),
calls the real reformulator, and checks must_contain / must_not_contain /
expect_unchanged. Skips cleanly when no LLM keys are configured.

Usage:
    PYTHONPATH=src python evals/run_reformulation_eval.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from contextlib import suppress
from pathlib import Path

DATASET = Path(__file__).parent / "golden" / "reformulation_dataset.jsonl"
PASS_THRESHOLD = 0.85


def load_cases(limit: int | None = None) -> list[dict]:
    cases = []
    for raw in DATASET.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if text:
            cases.append(json.loads(text))
    return cases[:limit] if limit else cases


def build_mem_inputs(case: dict) -> dict:
    history = case.get("history", [])
    turns = [
        {"user_query": h["q"], "agent_response": h["r"], "timestamp": float(i)}
        for i, h in enumerate(history)
    ]
    last = history[-1] if history else {}
    return {
        "working": {
            "turn_id": str(len(history)) if history else None,
            "previous_user_query": last.get("q", ""),
            "previous_system_response": last.get("r", ""),
            "current_raw_query": case["query"],
        },
        "sliding": {"turns": turns, "summary": {}, "count": len(turns)},
        "episodic": {"hits": [], "context": "", "count": 0},
    }


def check_case(case: dict, rewritten: str) -> tuple[bool, list[str]]:
    failures = []
    for token in case.get("must_contain", []):
        if token not in rewritten:
            failures.append(f"missing {token!r}")
    for token in case.get("must_not_contain", []):
        if token in rewritten:
            failures.append(f"leaked {token!r}")
    if case.get("expect_unchanged") and rewritten.strip() != case["query"].strip():
        failures.append("expected unchanged")
    return (not failures, failures)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        with suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    try:
        from application.agents.reformulator import QueryReformulator
        from infrastructure.llm.llm_provider import LLMProvider
    except Exception as e:
        print(f"SKIP: imports unavailable: {e}")
        return 0

    try:
        reformulator = QueryReformulator(LLMProvider())
    except Exception as e:
        print(f"SKIP: no LLM provider ({e})")
        return 0

    cases = load_cases(args.limit)
    passed, failed = 0, []
    start = time.time()
    for case in cases:
        try:
            rewritten, _, _ = reformulator.rewrite(
                case["query"], mem_inputs=build_mem_inputs(case), user_id="eval"
            )
        except Exception as e:
            failed.append((case["id"], [f"exception: {e}"]))
            continue
        ok, reasons = check_case(case, rewritten)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['id']}: {rewritten[:100]}")
        if not ok:
            print(f"       reasons: {reasons}")
            failed.append((case["id"], reasons))
        else:
            passed += 1

    total = len(cases)
    rate = passed / total if total else 1.0
    print(f"\n{passed}/{total} passed ({rate:.0%}) in {time.time() - start:.1f}s "
          f"(threshold {PASS_THRESHOLD:.0%})")
    return 0 if rate >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
