"""Unit tests for B5 spec validator."""

from application.services.dashboard.spec_validator import validate_chart_spec


def _valid_payload() -> dict:
    return {
        "chart_type": "line",
        "title": "Giá VNM",
        "x_field": "time",
        "y_field": "close",
        "series": [{"name": "VNM", "type": "line", "data_ref": "rows"}],
        "sort": {"field": "time", "order": "ascending"},
        "data": [{"time": "2026-03-01", "close": 61.8}],
    }


def test_validator_accepts_valid_spec():
    result = validate_chart_spec(_valid_payload())
    assert result.valid is True
    assert result.errors == []
    assert "series_non_empty" in result.checked_rules


def test_validator_rejects_unknown_y_field_with_actionable_error():
    payload = _valid_payload()
    payload["y_field"] = "close_price"
    result = validate_chart_spec(payload)
    assert result.valid is False
    assert any("close_price" in e and "close" in e for e in result.errors)
