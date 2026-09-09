"""B5 Spec Validator — rule-based, không gọi LLM. Dùng cho retry rẻ tiền."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from domain.entities.chart_spec import CHART_LIBRARY_ROUTE, ChartSpec


class SpecValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    checked_rules: list[str] = Field(default_factory=list)


def validate_chart_spec(spec: ChartSpec | dict[str, Any]) -> SpecValidationResult:
    checked: list[str] = []
    errors: list[str] = []
    if isinstance(spec, dict):
        try:
            spec = ChartSpec.model_validate(spec)
        except Exception as e:
            return SpecValidationResult(
                valid=False,
                errors=[f"schema_invalid: {e}"],
                checked_rules=["schema_parse"],
            )
    checked.append("chart_type_in_enum")
    if spec.chart_type.value not in CHART_LIBRARY_ROUTE:
        errors.append(f"chart_type '{spec.chart_type.value}' không thuộc enum hỗ trợ")
    checked.append("series_non_empty")
    if not spec.series:
        errors.append("series rỗng — cần ít nhất 1 series")
    rows = spec.data or []
    cols: set[str] = set()
    for r in rows:
        if isinstance(r, dict):
            cols.update(r.keys())
    checked.append("x_field_exists_in_data")
    if spec.x_field not in cols:
        errors.append(f"x_field '{spec.x_field}' không khớp field {sorted(cols)[:8]} trong data")
    checked.append("y_field_exists_in_data")
    if spec.y_field not in cols:
        errors.append(f"y_field '{spec.y_field}' không khớp field {sorted(cols)[:8]} trong data")
    checked.append("sort_field_valid")
    if spec.sort.field not in cols:
        errors.append(f"sort.field '{spec.sort.field}' không khớp field {sorted(cols)[:8]} trong data")
    if spec.library != CHART_LIBRARY_ROUTE.get(spec.chart_type.value, ""):
        errors.append(
            f"library '{spec.library}' sai route, kỳ vọng "
            f"'{CHART_LIBRARY_ROUTE.get(spec.chart_type.value)}' cho {spec.chart_type.value}"
        )
        checked.append("library_route_match")
    else:
        checked.append("library_route_match")
    return SpecValidationResult(valid=not errors, errors=errors, checked_rules=checked)
