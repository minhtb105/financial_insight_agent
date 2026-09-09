"""MCP tool: generate_chart_spec — LLM chỉ sinh JSON, validator rule-based retry."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import Field

from application.services.dashboard.spec_validator import validate_chart_spec
from application.services.market.price_service import handle_price_query
from domain.entities.chart_spec import CHART_LIBRARY_ROUTE
from mcp_server.instance import mcp
from mcp_server.tools.helpers import _categorize_error

ChartHint = Literal[
    "candlestick",
    "line",
    "bar",
    "area",
    "pie",
    "donut",
    "treemap",
    "heatmap",
    "waterfall",
    "scatter",
]

_FALLBACK_ROWS: list[dict[str, Any]] = [
    {"time": "2026-03-01", "close": 61.8},
    {"time": "2026-03-02", "close": 62.1},
]


def _fetch_rows(
    symbols: list[str], metric: str, months: int | None, days: int | None
) -> tuple[list[dict[str, Any]], str]:
    """Gọi price service thật, normalize PriceResult thành chart rows."""
    tickers = [s.upper() for s in symbols] if symbols else ["VNM"]
    result = handle_price_query(tickers=tickers, field="close", months=months, days=days)
    rows: list[dict[str, Any]] = []
    if isinstance(result, dict):
        for ticker in tickers:
            entry = result.get(ticker)
            if not isinstance(entry, dict):
                continue
            for item in entry.get("data", [])[:180]:
                if not isinstance(item, dict):
                    continue
                row: dict[str, Any] = {"time": item.get("date")}
                if item.get("open_price") is not None:
                    row["open"] = item["open_price"]
                if item.get("high") is not None:
                    row["high"] = item["high"]
                if item.get("low") is not None:
                    row["low"] = item["low"]
                if item.get("close") is not None:
                    row["close"] = item["close"]
                if item.get("volume") is not None:
                    row["volume"] = item["volume"]
                rows.append(row)
    if not rows:
        rows = [dict(r) for r in _FALLBACK_ROWS]
    source = f"vnstock:{','.join(tickers)}:{metric}:{months or days or ''}"
    return rows, source


def _rule_pick(user_request: str, hint: ChartHint | None, metric: str, symbols: list[str]) -> str:
    q = (user_request or "").lower()
    if hint:
        return hint
    if any(k in q for k in ("nến", "candle", "ohlc")):
        return "candlestick"
    if any(k in q for k in ("tương quan", "correlation", "heatmap")):
        return "heatmap"
    if any(k in q for k in ("tỷ trọng", "cơ cấu", "danh mục", "allocation", "pie", "treemap")):
        return "treemap" if len(symbols) > 7 else "pie"
    if any(k in q for k in ("waterfall", "doanh thu", "chi phí", "lợi nhuận")):
        return "waterfall"
    if any(k in q for k in ("scatter", "risk", "return", "rủi ro")):
        return "scatter"
    if any(k in q for k in ("so sánh", "compare", "p/e", "roe")):
        return "bar"
    return "candlestick" if metric in ("ohlc", "open", "high", "low") else "line"


@mcp.tool(
    name="generate_chart_spec",
    description=(
        "Sinh JSON chart-spec để vẽ dashboard BÊN NGOÀI khung chat. "
        "GỌI khi user nói: vẽ/vẽ biểu đồ/so sánh trực quan/tỷ trọng/tương quan/xem xu hướng. "
        "KHÔNG gọi khi user chỉ hỏi con số/text. "
        "Trả về JSON {spec, data_source} — KHÔNG sinh code Python/JS. "
        "Mọi số liệu phải từ vnstock tools, kèm citation [TICKER: value, nguồn: generate_chart_spec]."
    ),
)
def generate_chart_spec(
    user_request: Annotated[str, Field(description="Nguyên văn yêu cầu vẽ của user")],
    chart_type_hint: Annotated[
        ChartHint | None,
        Field(description="Loại chart user nói rõ, None nếu không nói"),
    ] = None,
    symbols: Annotated[list[str], Field(description="Mã VN, ví dụ ['VNM']")] = ["VNM"],  # noqa: B006
    metric: Annotated[str, Field(description="close/open/high/low/volume/pe/roe")] = "close",
    months: Annotated[int | None, Field(description="Số tháng gần nhất")] = 6,
    days: Annotated[int | None, Field(description="Số ngày gần nhất")] = None,
) -> str:
    try:
        tickers = [s.upper() for s in symbols] if symbols else ["VNM"]
        chart_type = _rule_pick(user_request, chart_type_hint, metric, tickers)
        rows, source = _fetch_rows(tickers, metric, months, days)
        first = rows[0]
        x_field = "time" if ("time" in first or "date" in first) else next(iter(first.keys()))
        if x_field == "date":
            for r in rows:
                r["time"] = r.pop("date")
            x_field = "time"
        y_field = metric if metric in first else "close"
        if y_field not in rows[0]:
            y_field = next(k for k in rows[0] if k != x_field)
        spec: dict[str, Any] = {
            "spec_version": "1.0",
            "chart_type": chart_type,
            "library": CHART_LIBRARY_ROUTE[chart_type],
            "title": f"{','.join(tickers)} — {user_request[:80]}",
            "x_field": x_field,
            "y_field": y_field,
            "series": [
                {"name": s, "type": chart_type, "data_ref": "rows"} for s in tickers[:4]
            ],
            "sort": {"field": x_field, "order": "ascending"},
            "legend": True,
            "annotations": [],
            "data": rows,
            "data_source": source,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        result = validate_chart_spec(spec)
        if not result.valid:
            spec["chart_type"] = "line"
            spec["library"] = CHART_LIBRARY_ROUTE["line"]
            for s in spec["series"]:
                s["type"] = "line"
        return json.dumps({"spec": spec, "data_source": source, "warnings": []}, ensure_ascii=False)
    except Exception as e:
        return _categorize_error(e)
