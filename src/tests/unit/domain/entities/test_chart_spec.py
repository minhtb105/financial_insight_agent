"""Unit tests for ChartSpec domain entity."""

from domain.entities.chart_spec import ChartSpec


def test_chart_spec_minimal_valid():
    spec = ChartSpec(
        chart_type="line",
        title="Giá đóng cửa VNM — 6 tháng gần nhất",
        x_field="time",
        y_field="close",
        series=[{"name": "VNM", "type": "line", "data_ref": "rows"}],
        sort={"field": "time", "order": "ascending"},
        data=[
            {"time": "2026-03-01", "close": 61.8},
            {"time": "2026-03-02", "close": 62.1},
        ],
        data_source="vnstock:VNM:close:6m",
    )
    assert spec.chart_type == "line"
    assert spec.library == "recharts"
    assert spec.spec_version == "1.0"
