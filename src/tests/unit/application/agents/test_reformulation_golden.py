"""Offline shape validation for the reformulation golden dataset (no LLM key needed)."""

import json
from pathlib import Path

DATASET = Path(__file__).parents[5] / "evals" / "golden" / "reformulation_dataset.jsonl"

REQUIRED = {"id", "history", "query", "must_contain", "must_not_contain", "expect_unchanged"}


def _load():
    cases = []
    for lineno, raw in enumerate(DATASET.read_text(encoding="utf-8").splitlines(), 1):
        text = raw.strip()
        if text:
            cases.append((lineno, json.loads(text)))
    return cases


def test_dataset_has_enough_cases():
    cases = _load()
    assert len(cases) >= 15, f"expected >=15 cases, got {len(cases)}"


def test_case_schema():
    for lineno, case in _load():
        assert set(case) >= REQUIRED, f"line {lineno}: missing keys"
        assert isinstance(case["history"], list)
        for turn in case["history"]:
            assert "q" in turn and "r" in turn, f"line {lineno}: bad turn"
        assert isinstance(case["query"], str) and case["query"].strip()
        assert isinstance(case["expect_unchanged"], bool)


def test_ids_unique():
    ids = [case["id"] for _, case in _load()]
    assert len(ids) == len(set(ids)), "duplicate case ids"


def test_covers_required_patterns():
    ids = [case["id"] for _, case in _load()]
    assert any("drift" in i for i in ids), "need topic-drift cases"
    assert any("no_history" in i or "self_contained" in i for i in ids), "need passthrough cases"
