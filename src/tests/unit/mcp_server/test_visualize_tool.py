"""Unit tests for generate_chart_spec MCP tool — mock service, không gọi vnstock."""

import json
from unittest.mock import patch

import mcp_server.tools.visualize as viz


def test_generate_chart_spec_returns_valid_spec_json():
    fake_rows = [
        {"time": "2026-03-01", "close": 61.8},
        {"time": "2026-03-02", "close": 62.1},
    ]
    with patch.object(viz, "_fetch_rows", return_value=(fake_rows, "vnstock:VNM:close:6m")):
        raw = viz.generate_chart_spec(
            user_request="Vẽ giá VNM 6 tháng",
            chart_type_hint=None,
            symbols=["VNM"],
            metric="close",
            months=6,
        )
    payload = json.loads(raw)
    assert payload["spec"]["chart_type"] in ("line", "candlestick")
    assert payload["spec"]["x_field"] == "time"


def test_generate_chart_spec_explicit_hint_respected():
    fake_rows = [
        {"time": "2026-03-01", "close": 61.8},
        {"time": "2026-03-02", "close": 62.1},
    ]
    with patch.object(viz, "_fetch_rows", return_value=(fake_rows, "vnstock:VNM:close:6m")):
        raw = viz.generate_chart_spec(
            user_request="Vẽ biểu đồ nến VNM",
            chart_type_hint="candlestick",
            symbols=["VNM"],
            metric="close",
            months=6,
        )
    payload = json.loads(raw)
    assert payload["spec"]["chart_type"] == "candlestick"
    assert payload["spec"]["library"] == "tradingview-lightweight-charts"


def test_fetch_rows_normalizes_price_service_shape():
    from mcp_server.tools import visualize as viz_mod

    service_result = {
        "VNM": {
            "ticker": "VNM",
            "data": [
                {
                    "date": "2026-03-01",
                    "open_price": 61.2,
                    "high": 62.0,
                    "low": 60.8,
                    "close": 61.8,
                    "volume": 1520000,
                }
            ],
            "start_date": "2026-03-01",
            "end_date": "2026-03-01",
        }
    }
    with patch("mcp_server.tools.visualize.handle_price_query", return_value=service_result):
        rows, source = viz_mod._fetch_rows(["VNM"], "close", 6, None)
    assert rows[0]["time"] == "2026-03-01"
    assert rows[0]["close"] == 61.8
    assert "VNM" in source
