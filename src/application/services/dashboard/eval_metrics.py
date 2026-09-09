"""Offline eval metrics cho text-to-dashboard — rule-based trên JSON, không cần vision/LLM.

Ba tầng mượn từ VisEval, đơn giản hóa nhờ output là JSON chart-spec:
- Validity: spec có pass SpecValidator không.
- Legality: chart_type/x_field/y_field/sort có khớp ground truth không (so JSON trực tiếp).
- Readability: rule trên JSON (title, labels, pie slices, row cap) → score 1-5.
- Quality: 0 nếu invalid/illegal, ngược lại = readability.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LegalityResult(BaseModel):
    chart_type_ok: bool = False
    x_ok: bool = False
    y_ok: bool = False
    sort_ok: bool = False

    @property
    def all_ok(self) -> bool:
        return self.chart_type_ok and self.x_ok and self.y_ok and self.sort_ok


class ReadabilityResult(BaseModel):
    score: int = Field(..., ge=1, le=5)
    failed_rules: list[str] = Field(default_factory=list)


_READABILITY_RULES = ("title_ok", "series_labels_ok", "pie_slices_ok", "row_cap_ok")


def legality_compare(spec: dict[str, Any], expected: dict[str, Any]) -> LegalityResult:
    """So trực tiếp JSON spec với ground truth, không cần render."""
    sort = spec.get("sort") or {}
    return LegalityResult(
        chart_type_ok=spec.get("chart_type") == expected.get("chart_type"),
        x_ok=spec.get("x_field") == expected.get("x_field"),
        y_ok=spec.get("y_field") == expected.get("y_field"),
        sort_ok=(
            sort.get("field") == expected.get("sort_field")
            and sort.get("order") == expected.get("sort_order", "ascending")
        ),
    )


def readability_score(spec: dict[str, Any]) -> ReadabilityResult:
    """Rule-based 1-5: 5 điểm trừ 1 cho mỗi rule fail."""
    failed: list[str] = []
    if not str(spec.get("title", "")).strip():
        failed.append("title_ok")
    series = spec.get("series") or []
    if not series or any(not str(s.get("name", "")).strip() for s in series if isinstance(s, dict)):
        failed.append("series_labels_ok")
    rows = spec.get("data") or []
    n_rows = len(rows) if isinstance(rows, list) else 0
    if spec.get("chart_type") in ("pie", "donut") and n_rows > 7:
        failed.append("pie_slices_ok")
    if n_rows == 0 or n_rows > 200:
        failed.append("row_cap_ok")
    score = max(1, 5 - len(failed))
    return ReadabilityResult(score=score, failed_rules=failed)


def quality_score(valid: bool, legality: LegalityResult, readability: ReadabilityResult) -> int:
    """Theo công thức VisEval: 0 nếu invalid/illegal, ngược lại = readability."""
    if not valid or not legality.chart_type_ok:
        return 0
    return readability.score
