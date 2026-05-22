"""Unit tests for domain entities."""

from datetime import datetime, timezone, timedelta
import pytest
from domain.entities.time_range import TimeRange


def test_time_range_resolve_start_only():
    tr = TimeRange(start="2024-01-01")
    result = tr.resolve()
    assert result["start"] == "2024-01-01"
    assert "end" in result


def test_time_range_resolve_end_only():
    tr = TimeRange(end="2024-06-01")
    result = tr.resolve()
    assert "start" in result
    assert result["end"] == "2024-06-01"


def test_time_range_resolve_both():
    tr = TimeRange(start="2024-01-01", end="2024-06-01")
    result = tr.resolve()
    assert result["start"] == "2024-01-01"
    assert result["end"] == "2024-06-01"


def test_time_range_resolve_days():
    tr = TimeRange(days=7)
    result = tr.resolve()
    assert "start" in result
    assert "end" in result


def test_time_range_resolve_special_end_yesterday():
    tr = TimeRange(end="yesterday")
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["end"] == "2026-03-09"


def test_time_range_resolve_special_end_today():
    tr = TimeRange(end="today")
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["end"] == "2026-03-10"


def test_time_range_resolve_special_end_last_week():
    tr = TimeRange(end="last_week")
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["end"] == "2026-03-03"


def test_time_range_resolve_special_end_last_month_january():
    tr = TimeRange(end="last_month")
    result = tr.resolve(now=datetime(2026, 1, 15))
    assert result["end"] == "2025-12-15"


def test_time_range_resolve_special_end_last_month_march_31():
    tr = TimeRange(end="last_month")
    result = tr.resolve(now=datetime(2026, 3, 31))
    assert result["end"] == "2026-02-28"


def test_time_range_resolve_special_end_unchanged():
    tr = TimeRange(end="2026-06-01")
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["end"] == "2026-06-01"


def test_time_range_resolve_start_only_with_fixed_now():
    tr = TimeRange(start="2026-01-15")
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["start"] == "2026-01-15"
    assert result["end"] == "2026-03-10"


def test_time_range_resolve_end_yesterday_only():
    tr = TimeRange(end="yesterday")
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["end"] == "2026-03-09"


def test_time_range_resolve_years_leap():
    tr = TimeRange(years=1)
    result = tr.resolve(now=datetime(2024, 2, 29))
    assert result["start"] == "2023-02-28"
    assert result["end"] == "2024-02-29"


def test_time_range_resolve_fallback_30_days():
    tr = TimeRange(end="2026-03-10")
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["start"] == "2026-02-08"


def test_time_range_resolve_no_params():
    tr = TimeRange()
    result = tr.resolve(now=datetime(2026, 3, 10))
    assert result["start"] == "2026-03-10"
    assert result["end"] == "2026-03-10"


def test_time_range_resolve_end_ambiguous_raises():
    with pytest.raises(ValueError):
        TimeRange(start="2026-01-01", days=7)


def test_subtract_months_positive():
    result = TimeRange.subtract_months(datetime(2026, 5, 15), 3)
    assert result == datetime(2026, 2, 15)


def test_subtract_months_across_year():
    result = TimeRange.subtract_months(datetime(2026, 2, 15), 3)
    assert result.month == 11
    assert result.year == 2025


def test_subtract_months_feb29():
    result = TimeRange.subtract_months(datetime(2024, 3, 31), 1)
    assert result.day == 29
    assert result.month == 2


def test_subtract_months_many():
    result = TimeRange.subtract_months(datetime(2026, 3, 10), 18)
    assert result.year == 2024
    assert result.month == 9





