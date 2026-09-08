"""Shared stats helpers — single source for aggregation/ranking/compare logic.

Extracted from duplicate implementations in:
- application/services/financial/aggregate_service.py
- application/services/financial/ranking_service.py
- application/services/market/compare_service.py
"""

import math
from typing import Any

from shared.utils.calculations import calculate_std_dev


def extract_field_values(data: list[dict[str, Any]], field: str) -> list[float]:
    """Extract valid numeric values for *field* from a list of price records.

    Filters out ``None`` and ``NaN`` (``v != v``) and non-numeric entries.
    """
    values: list[float] = []
    for item in data:
        if field not in item:
            continue
        v = item[field]
        if v is None:
            continue
        try:
            fv = float(v)
            if fv != fv:  # NaN
                continue
            values.append(fv)
        except (TypeError, ValueError):
            continue
    return values


def compute_basic_stats(values: list[float]) -> dict[str, Any]:
    """Compute mean/min/max/median/std/sum for *values*."""
    if not values:
        return {"error": "No values"}
    n = len(values)
    sorted_vals = sorted(values)
    mean_val = sum(values) / n
    median_val = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    return {
        "mean": mean_val,
        "min": min(values),
        "max": max(values),
        "median": median_val,
        "std": calculate_std_dev(values),
        "sum": sum(values),
        "count": n,
    }


def aggregate_values(values: list[float], func: str) -> float:
    """Aggregate *values* with *func* (mean/sum/median/std/min/max/latest)."""
    if not values:
        return 0.0
    n = len(values)
    sorted_vals = sorted(values)
    if func == "mean":
        return sum(values) / n
    if func == "sum":
        return sum(values)
    if func == "median":
        return sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    if func == "std":
        return calculate_std_dev(values)
    if func == "min":
        return min(values)
    if func == "max":
        return max(values)
    if func == "latest":
        return values[-1]
    # default fallback mirrors original services
    return sum(values) / n


def is_valid_number(v: Any) -> bool:
    """Check if *v* is a valid finite number (not None/NaN)."""
    if v is None:
        return False
    try:
        fv = float(v)
        return fv == fv and not math.isinf(fv)
    except (TypeError, ValueError):
        return False
