"""Validate the golden dataset: schema, unique ids, tickers, tool names.

Usage::

    python evals/scripts/validate_golden_dataset.py [path-to-jsonl]

Exit code 0 = valid, 1 = invalid (errors printed).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_DATASET = Path(__file__).parent.parent / "golden" / "golden_dataset.jsonl"

REQUIRED_FIELDS = {"id", "query_type", "query", "expected_tools"}
OPTIONAL_FIELDS = {"ground_truth", "as_of_date", "difficulty", "notes"}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

VALID_QUERY_TYPES = {
    "price", "indicator", "compare", "ranking", "aggregate",
    "financial_ratio", "company", "news_sentiment", "portfolio",
    "alert", "forecast", "sector",
    "compound_sequential", "compound_multi_intent",
    "edge_invalid_ticker", "edge_ambiguous",
}

VALID_DIFFICULTY = {"easy", "medium", "hard"}


def _load_valid_tickers() -> frozenset:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    try:
        from infrastructure.guardrails.tickers import VIETNAMESE_TICKERS

        return VIETNAMESE_TICKERS
    except Exception:
        print("WARN: could not import VIETNAMESE_TICKERS — ticker check skipped")
        return frozenset()


def _extract_tickers(query: str, known: frozenset) -> list[str]:
    candidates = set(re.findall(r"\b[A-Z]{3,4}\b", query))
    if not known:
        return sorted(candidates)
    return sorted(candidates & set(known))


def validate(dataset_path: Path) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    valid_tickers = _load_valid_tickers()

    try:
        from application.agents.tool_registry import ALL_TOOLS

        valid_tools = {t.name for t in ALL_TOOLS}
    except Exception:
        print("WARN: could not import ALL_TOOLS — tool name check skipped")
        valid_tools = None

    lines = dataset_path.read_text(encoding="utf-8").splitlines()
    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: invalid JSON ({exc})")
            continue

        missing = REQUIRED_FIELDS - set(case)
        if missing:
            errors.append(f"line {lineno}: missing fields {sorted(missing)}")
            continue

        cid = case["id"]
        if cid in seen_ids:
            errors.append(f"line {lineno}: duplicate id '{cid}'")
        seen_ids.add(cid)

        if not str(case["query"]).strip():
            errors.append(f"line {lineno} [{cid}]: empty query")
        if len(str(case["query"])) > 1000:
            errors.append(f"line {lineno} [{cid}]: query exceeds 1000 chars")

        if case["query_type"] not in VALID_QUERY_TYPES:
            errors.append(f"line {lineno} [{cid}]: unknown query_type '{case['query_type']}'")

        difficulty = case.get("difficulty")
        if difficulty is not None and difficulty not in VALID_DIFFICULTY:
            errors.append(f"line {lineno} [{cid}]: invalid difficulty '{difficulty}'")

        as_of = case.get("as_of_date")
        if as_of is not None and not (isinstance(as_of, str) and _DATE_RE.match(as_of)):
            errors.append(f"line {lineno} [{cid}]: as_of_date must be YYYY-MM-DD or null")

        tools = case.get("expected_tools") or []
        if valid_tools is not None:
            unknown_tools = [t for t in tools if t not in valid_tools]
            if unknown_tools:
                errors.append(f"line {lineno} [{cid}]: unknown tools {unknown_tools}")

        gt = case.get("ground_truth")
        if gt is not None and not isinstance(gt, dict):
            errors.append(f"line {lineno} [{cid}]: ground_truth must be object or null")

        if valid_tickers and case["query_type"].startswith("edge"):
            pass  # edge cases intentionally use invalid/missing tickers
        elif valid_tickers and case["query_type"] == "sector":
            pass  # sector queries target an industry, not a specific ticker
        elif valid_tickers:
            mentioned = _extract_tickers(case["query"], valid_tickers)
            if not mentioned:
                errors.append(
                    f"line {lineno} [{cid}]: no known ticker found in query "
                    f"(check spelling against guardrails/tickers.py)"
                )

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    if not path.exists():
        print(f"Dataset not found: {path}")
        return 1
    n_cases = sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
    print(f"Validating {path} ({n_cases} cases)...")
    errors = validate(path)
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK — dataset is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
