"""Unit tests for offline eval metrics (pure, không cần LLM/vision)."""

from application.services.dashboard.eval_metrics import (
    legality_compare,
    quality_score,
    readability_score,
)


def _spec(**overrides):
    base = {
        "chart_type": "line",
        "title": "Giá VNM",
        "x_field": "time",
        "y_field": "close",
        "series": [{"name": "VNM", "type": "line", "data_ref": "rows"}],
        "sort": {"field": "time", "order": "ascending"},
        "data": [{"time": "2026-03-01", "close": 61.8}],
    }
    base.update(overrides)
    return base


def _expected(**overrides):
    base = {
        "chart_type": "line",
        "x_field": "time",
        "y_field": "close",
        "sort_field": "time",
        "sort_order": "ascending",
    }
    base.update(overrides)
    return base


def test_legality_all_ok():
    result = legality_compare(_spec(), _expected())
    assert result.all_ok is True


def test_legality_wrong_chart_type():
    result = legality_compare(_spec(chart_type="bar"), _expected())
    assert result.chart_type_ok is False
    assert result.x_ok is True


def test_legality_wrong_sort_order():
    spec = _spec()
    spec["sort"] = {"field": "time", "order": "descending"}
    result = legality_compare(spec, _expected())
    assert result.sort_ok is False


def test_readability_full_score():
    result = readability_score(_spec())
    assert result.score == 5
    assert result.failed_rules == []


def test_readability_pie_too_many_slices():
    spec = _spec(
        chart_type="pie",
        data=[{"symbol": f"S{i}", "value": i} for i in range(12)],
    )
    result = readability_score(spec)
    assert result.score == 4
    assert "pie_slices_ok" in result.failed_rules


def test_readability_missing_title_and_empty_data():
    result = readability_score(_spec(title="  ", data=[]))
    assert result.score == 3
    assert "title_ok" in result.failed_rules
    assert "row_cap_ok" in result.failed_rules


def test_quality_zero_when_invalid_or_wrong_type():
    leg = legality_compare(_spec(), _expected())
    read = readability_score(_spec())
    assert quality_score(False, leg, read) == 0
    bad_leg = legality_compare(_spec(chart_type="bar"), _expected())
    assert quality_score(True, bad_leg, read) == 0


def test_quality_equals_readability_when_good():
    leg = legality_compare(_spec(), _expected())
    read = readability_score(_spec())
    assert quality_score(True, leg, read) == 5
