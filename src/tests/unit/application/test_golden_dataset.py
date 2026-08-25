"""Unit tests validating the shipped golden dataset structure."""

import json
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).parents[4] / "evals"
sys.path.insert(0, str(EVALS_DIR / "scripts"))

from validate_golden_dataset import validate  # noqa: E402

DATASET = EVALS_DIR / "golden" / "golden_dataset.jsonl"


def test_golden_dataset_exists_and_is_valid():
    assert DATASET.exists(), f"missing {DATASET}"
    errors = validate(DATASET)
    assert errors == [], "\n".join(errors)


def test_golden_dataset_covers_all_query_types():
    cases = [
        json.loads(ln)
        for ln in DATASET.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    types = {c["query_type"] for c in cases}
    expected = {
        "price", "indicator", "compare", "ranking", "aggregate",
        "financial_ratio", "company", "news_sentiment", "portfolio",
        "alert", "forecast", "sector",
        "compound_sequential", "compound_multi_intent",
        "edge_invalid_ticker", "edge_ambiguous",
    }
    missing = expected - types
    assert not missing, f"query types missing from dataset: {missing}"


def test_numeric_cases_have_ground_truth():
    cases = [
        json.loads(ln)
        for ln in DATASET.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    numeric = [
        c for c in cases
        if c["query_type"] in ("price", "indicator")
        and c.get("as_of_date")  # fixed-date cases only; realtime ones are soft-checked
    ]
    assert numeric, "expected at least one numeric fixed-date case"
    for case in numeric:
        gt = case.get("ground_truth")
        if isinstance(gt, dict) and gt.get("needs_snapshot"):
            continue  # documented upstream data-source gap
        assert isinstance(gt, dict) and any(
            v is not None and k != "needs_snapshot" for k, v in gt.items()
        ), f"{case['id']} lacks ground truth values"


def test_case_count_in_expected_range():
    n = sum(
        1
        for ln in DATASET.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    )
    assert 30 <= n <= 50, f"dataset size {n} outside planned range"
