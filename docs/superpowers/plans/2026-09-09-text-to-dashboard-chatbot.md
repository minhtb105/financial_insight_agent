# Text-to-Dashboard in Chatbot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** User gõ tiếng Việt trong chatbot → DashboardPanel ngoài khung chat auto-render 1 biểu đồ lớn, tương tác được (đổi loại/timeframe/ticker), hỏi follow-up về chart đó mà không mất chart.

**Architecture:** ReAct-native, 1 MCP tool `generate_chart_spec` sinh JSON ChartSpec v1.0 (LLM chỉ sinh JSON, không sinh code). Backend rule-first selector + rule-based validator retry ≤2. SSE thêm `chart_spec`/`chart_error`. Frontend dumb `switch(chart_type)` + linked 2-pane Chat|Dashboard + tabs lịch sử spec + `activeChartSpec` gửi kèm query.

**Tech Stack:** FastAPI + LangGraph ReAct + FastMCP, Pydantic v2, Next.js 16 + Recharts (sẵn có) + lightweight-charts (candlestick) + echarts-for-react (heatmap/treemap), Zod mirror ở client, pytest + ruff + black.

**Spec:** `.opencode/plans/Plan-TextToDashboard-Agent.md` (pipeline B1-B6, enum chart, schema B4/B5) + `.opencode/plans/PhanBien-KeHoach-FollowUpQ-Dashboard-Eval.md` (mục 2.3/2.5/Phase 4-5) + quyết định đã chốt: bỏ intent-router riêng, không mini-LLM frontend, default = agent-chọn (intent+data), dropdown = override qua regenerate.

## Global Constraints

- Chỉ giáo dục, không khuyến nghị mua/bán cá nhân; mọi chart có citation `[TICKER: value, nguồn: tool]` + disclaimer `Thông tin chỉ mang tính giáo dục, không phải lời khuyên đầu tư.`
- Tiếng Việt là mặc định cho title/labels user-facing.
- LLM chỉ sinh JSON ChartSpec v1.0, không sinh code Python/JS; `library` suy từ bảng route cứng, không để LLM tự chọn.
- 1 query → đúng 1 spec → đúng 1 chart; không render 9 chart/query.
- SSE backward-compatible: client cũ bỏ qua event lạ, không vỡ `chunk/final/error`.
- `pytest`: `testpaths=["src/tests"]`, `pythonpath=["src"]`; ruff line-length 100; black line-length 100.
- Frontend a11y cơ bản: controls có label, chart có title, keyboard dùng được dropdown.

---
### Task 1: P0 — ChartSpec domain entity (contract gốc)

**Files:**
- Create: `src/domain/entities/chart_spec.py`
- Modify: `src/domain/entities/__init__.py`
- Test: `src/tests/unit/domain/entities/test_chart_spec.py`

**Interfaces:**
- Consumes: `src/domain/entities/time_range.py:validate_ticker_list` (pattern ticker, không import trực tiếp để tránh cycle — copy regex `^[A-Z0-9]{2,8}$`).
- Produces: `ChartType(str, Enum)` với 10 giá trị (9 nhóm, pie/donut chung nhóm), `ChartSort(BaseModel)`, `ChartSeries(BaseModel)`, `ChartSpec(BaseModel)`, `CHART_LIBRARY_ROUTE: dict[str, str]`, `SUITABILITY_HINTS: dict[str, str]` cho P2 dropdown warning. Later tasks dùng đúng tên này.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest src/tests/unit/domain/entities/test_chart_spec.py::test_chart_spec_minimal_valid -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain.entities.chart_spec'`

- [ ] **Step 3: Write minimal implementation**

```python
"""ChartSpec v1.0 — contract duy nhất giữa LLM, validator, SSE và frontend."""
from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class ChartType(str, Enum):
    CANDLESTICK = "candlestick"
    LINE = "line"
    BAR = "bar"
    AREA = "area"
    PIE = "pie"
    DONUT = "donut"
    TREEMAP = "treemap"
    HEATMAP = "heatmap"
    WATERFALL = "waterfall"
    SCATTER = "scatter"


CHART_LIBRARY_ROUTE: dict[str, str] = {
    "candlestick": "tradingview-lightweight-charts",
    "line": "recharts",
    "bar": "recharts",
    "area": "recharts",
    "pie": "recharts",
    "donut": "recharts",
    "waterfall": "recharts",
    "scatter": "recharts",
    "heatmap": "echarts",
    "treemap": "echarts",
}

SUITABILITY_HINTS: dict[str, str] = {
    "candlestick": "Giá OHLC 1 mã theo thời gian.",
    "line": "Xu hướng theo thời gian, so sánh nhiều mã.",
    "bar": "So sánh rời rạc giữa mã/kỳ (P/E, ROE...).",
    "area": "Tăng trưởng tích lũy.",
    "pie": "Tỷ trọng ≤6 hạng mục.",
    "donut": "Tỷ trọng ≤6 hạng mục (biến thể pie).",
    "treemap": "Tỷ trọng >7 hạng mục.",
    "heatmap": "Ma trận tương quan.",
    "waterfall": "Doanh thu → chi phí → lợi nhuận.",
    "scatter": "Risk vs return.",
}


class ChartSeries(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    data_ref: str = Field(default="rows")


class ChartSort(BaseModel):
    field: str = Field(..., min_length=1)
    order: Literal["ascending", "descending"] = "ascending"


class ChartSpec(BaseModel):
    spec_version: Literal["1.0"] = "1.0"
    chart_type: ChartType
    library: str = Field(default="")
    title: str = Field(..., min_length=1, max_length=200)
    x_field: str = Field(..., min_length=1, max_length=64)
    y_field: str = Field(..., min_length=1, max_length=64)
    series: list[ChartSeries] = Field(..., min_length=1)
    sort: ChartSort
    legend: bool = True
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(..., min_length=1)
    data_source: str = Field(default="", max_length=300)
    fetched_at: str = Field(default="", max_length=64)

    @model_validator(mode="after")
    def _derive_library(self):
        route = CHART_LIBRARY_ROUTE.get(self.chart_type.value, "")
        if not self.library:
            self.library = route
        return self

    @field_validator("x_field", "y_field")
    @classmethod
    def _no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("field must not contain spaces")
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest src/tests/unit/domain/entities/test_chart_spec.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Export from package init**

```python
from .chart_spec import (
    CHART_LIBRARY_ROUTE,
    SUITABILITY_HINTS,
    ChartSeries,
    ChartSort,
    ChartSpec,
    ChartType,
)
from .time_range import TimeRange

__all__ = [
    "CHART_LIBRARY_ROUTE",
    "SUITABILITY_HINTS",
    "ChartSeries",
    "ChartSort",
    "ChartSpec",
    "ChartType",
    "TimeRange",
]
```

File: `src/domain/entities/__init__.py` (thay toàn bộ nội dung 5 dòng cũ bằng khối trên).

Run: `python -m pytest src/tests/unit/domain/entities/test_domain_entities.py -v`
Expected: PASS (21 passed, không vỡ TimeRange)

- [ ] **Step 6: Commit**

```bash
git add src/domain/entities/chart_spec.py src/domain/entities/__init__.py src/tests/unit/domain/entities/test_chart_spec.py
git commit -m "feat(dashboard): add ChartSpec v1.0 domain entity"
```

---
### Task 2: P0 — Spec validator rule-based (B5)

**Files:**
- Create: `src/application/services/dashboard/__init__.py`
- Create: `src/application/services/dashboard/spec_validator.py`
- Test: `src/tests/unit/application/services/dashboard/test_spec_validator.py`

**Interfaces:**
- Consumes: `ChartSpec` từ Task 1 (import `from domain.entities.chart_spec import CHART_LIBRARY_ROUTE, ChartSpec`).
- Produces: `SpecValidationResult(BaseModel: valid: bool, errors: list[str], checked_rules: list[str])`, `validate_chart_spec(spec: ChartSpec | dict) -> SpecValidationResult`. P1 MCP tool gọi đúng tên này để retry.

- [ ] **Step 1: Write the failing test**

```python
"""Unit tests for B5 spec validator."""
from application.services.dashboard.spec_validator import validate_chart_spec
from domain.entities.chart_spec import ChartSpec


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest src/tests/unit/application/services/dashboard/test_spec_validator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.services.dashboard'`

- [ ] **Step 3: Write minimal implementation**

```python
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
        errors.append(
            f"x_field '{spec.x_field}' không khớp field {sorted(cols)[:8]} trong data"
        )
    checked.append("y_field_exists_in_data")
    if spec.y_field not in cols:
        errors.append(
            f"y_field '{spec.y_field}' không khớp field {sorted(cols)[:8]} trong data"
        )
    checked.append("sort_field_valid")
    if spec.sort.field not in cols:
        errors.append(
            f"sort.field '{spec.sort.field}' không khớp field {sorted(cols)[:8]} trong data"
        )
    if spec.library != CHART_LIBRARY_ROUTE.get(spec.chart_type.value, ""):
        errors.append(
            f"library '{spec.library}' sai route, kỳ vọng "
            f"'{CHART_LIBRARY_ROUTE.get(spec.chart_type.value)}' cho {spec.chart_type.value}"
        )
        checked.append("library_route_match")
    else:
        checked.append("library_route_match")
    return SpecValidationResult(valid=not errors, errors=errors, checked_rules=checked)
```

`src/application/services/dashboard/__init__.py` nội dung:

```python
from .spec_validator import SpecValidationResult, validate_chart_spec

__all__ = ["SpecValidationResult", "validate_chart_spec"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest src/tests/unit/application/services/dashboard/test_spec_validator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/application/services/dashboard/__init__.py src/application/services/dashboard/spec_validator.py src/tests/unit/application/services/dashboard/test_spec_validator.py
git commit -m "feat(dashboard): add B5 rule-based spec validator"
```

---
### Task 3: P0 — SSE + API contract (backend)

**Files:**
- Modify: `src/interfaces/api/app.py`
- Test: `src/tests/unit/interfaces/api/test_chart_sse_contract.py`

**Interfaces:**
- Consumes: `ChartSpec` (Task 1) chỉ để serialize ví dụ trong test, không import nặng vào app.
- Produces: helpers `_sse_chart_spec_event(spec_json: str, request_id: str) -> str`, `_sse_chart_error_event(detail, request_id) -> str`; mở rộng `QueryRequest` thêm `activeChartSpec: dict | None = None`. P1 stream dùng đúng 2 helper này.

- [ ] **Step 1: Write the failing test**

```python
"""SSE contract cho chart — backward compatible với parser cũ."""
from interfaces.api.app import _sse_chart_error_event, _sse_chart_spec_event


def test_chart_spec_event_shape():
    evt = _sse_chart_spec_event('{"chart_type":"line"}', "rid-1")
    assert evt.startswith("event: chart_spec\n")
    assert '"chart_type":"line"' in evt
    assert evt.endswith("\n\n")


def test_chart_error_event_shape():
    evt = _sse_chart_error_event("bad spec", "rid-2")
    assert evt.startswith("event: chart_error\n")
    assert "bad spec" in evt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest src/tests/unit/interfaces/api/test_chart_sse_contract.py -v`
Expected: FAIL with `ImportError: cannot import name '_sse_chart_spec_event'`

- [ ] **Step 3: Write minimal implementation**

Trong `src/interfaces/api/app.py`, ngay sau `_sse_error_event` (dòng 137-139), thêm:

```python
def _sse_chart_spec_event(spec_json: str, request_id: str) -> str:
    payload = {"request_id": request_id, "spec": spec_json}
    import json as _json

    return f"event: chart_spec\ndata: {_json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_chart_error_event(detail: str, request_id: str) -> str:
    return f"event: chart_error\ndata: {detail[:500]}\n\n"
```

Mở rộng `QueryRequest` (dòng 91-97):

```python
class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=_MAX_QUERY_LENGTH,
        description="Vietnamese stock market question",
    )
    activeChartSpec: dict | None = Field(
        default=None,
        description="ChartSpec đang pinned ở DashboardPanel (để follow-up về chart)",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest src/tests/unit/interfaces/api/test_chart_sse_contract.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/interfaces/api/app.py src/tests/unit/interfaces/api/test_chart_sse_contract.py
git commit -m "feat(dashboard): add chart SSE contract and activeChartSpec field"
```

---
### Task 4: P0 — Frontend chart-spec mirror (Zod + dumb router + SSE parse)

**Files:**
- Create: `frontend/src/lib/chart-spec.ts`
- Test thủ công: `cd frontend && npx tsc --noEmit` (repo chưa có vitest; không thêm framework test ở P0)

**Interfaces:**
- Consumes: JSON từ `event: chart_spec` của Task 3.
- Produces: `CHART_TYPES: readonly string[]` (10 giá trị khớp backend enum), `ChartSpec` (Zod infer), `parseChartSpecEvent(data: string)`, `routeChartKind(chart_type: string): "tradingview" | "recharts" | "echarts"`, `suitabilityWarning(chart_type, rowCount, seriesCount): string | null`. P2 renderer và P3 panel dùng đúng tên này.

- [ ] **Step 1: Write the implementation (mirror 1-1 với backend)**

```typescript
import { z } from "zod"

export const CHART_TYPES = [
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
] as const
export type ChartType = (typeof CHART_TYPES)[number]

const seriesSchema = z.object({
  name: z.string().min(1),
  type: z.string().min(1),
  data_ref: z.string().default("rows"),
})

export const chartSpecSchema = z.object({
  spec_version: z.literal("1.0").default("1.0"),
  chart_type: z.enum(CHART_TYPES),
  library: z.string().default(""),
  title: z.string().min(1).max(200),
  x_field: z.string().min(1).max(64),
  y_field: z.string().min(1).max(64),
  series: z.array(seriesSchema).min(1),
  sort: z.object({
    field: z.string().min(1),
    order: z.enum(["ascending", "descending"]).default("ascending"),
  }),
  legend: z.boolean().default(true),
  annotations: z.array(z.record(z.string(), z.unknown())).default([]),
  data: z.array(z.record(z.string(), z.unknown())).min(1),
  data_source: z.string().max(300).default(""),
  fetched_at: z.string().max(64).default(""),
})
export type ChartSpec = z.infer<typeof chartSpecSchema>

export function parseChartSpecEvent(data: string): ChartSpec | null {
  try {
    const outer = JSON.parse(data) as { spec?: string | Record<string, unknown> }
    const raw = typeof outer.spec === "string" ? JSON.parse(outer.spec) : outer.spec
    return chartSpecSchema.parse(raw)
  } catch {
    return null
  }
}

export function routeChartKind(chart_type: string): "tradingview" | "recharts" | "echarts" {
  if (chart_type === "candlestick") return "tradingview"
  if (chart_type === "heatmap" || chart_type === "treemap") return "echarts"
  return "recharts"
}

export function suitabilityWarning(
  chart_type: ChartType,
  rowCount: number,
  seriesCount: number,
): string | null {
  if ((chart_type === "pie" || chart_type === "donut") && rowCount > 7)
    return `Pie/donut kém đọc khi >7 lát (đang có ${rowCount}). Nên dùng treemap hoặc bar.`
  if (chart_type === "candlestick" && seriesCount > 1)
    return "Candlestick hợp nhất với 1 mã OHLC. So sánh nhiều mã nên dùng line."
  if (chart_type === "heatmap" && seriesCount < 2)
    return "Heatmap cần ≥2 mã/chỉ số để có ma trận tương quan."
  return null
}
```

- [ ] **Step 2: Run typecheck to verify it passes**

Run: `cd frontend; if ($?) { npx tsc --noEmit }`
Expected: PASS (no output, exit 0). Nếu lỗi `z.record` ở zod v4, đổi sang `z.record(z.string(), z.unknown())` đã đúng — không đổi sang `z.object({})`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/chart-spec.ts
git commit -m "feat(dashboard): add frontend chart-spec mirror and dumb router"
```

---
### Task 5: P1 — MCP tool generate_chart_spec (1 tool, enum 9 nhóm)

**Files:**
- Create: `src/mcp_server/tools/visualize.py`
- Modify: `src/mcp_server/tools/__init__.py` (thêm `from . import visualize`)
- Test: `src/tests/unit/mcp_server/test_visualize_tool.py` (mock `call_service`, không gọi vnstock thật)

**Interfaces:**
- Consumes: `validate_chart_spec` (Task 2), `ChartSpec` (Task 1), `call_service` helper hiện có.
- Produces: `generate_chart_spec(user_request, chart_type_hint, symbols, metric, months, days) -> str` trả JSON `{spec, data_source, fetched_at, warnings}`. Agent ReAct gọi qua MCP tools/list, P3 stream đọc đúng JSON này.

- [ ] **Step 1: Write the failing test**

```python
"""MCP visualize tool — mock service, không gọi vnstock."""
from unittest.mock import patch
import json
import mcp_server.tools.visualize as viz


def test_generate_chart_spec_returns_valid_spec_json():
    fake_rows = [
        {"time": "2026-03-01", "close": 61.8},
        {"time": "2026-03-02", "close": 62.1},
    ]
    with patch.object(viz, "_fetch_rows", return_value=(fake_rows, "vnstock:VNM:close:6m")):
        raw = viz.generate_chart_spec.func(
            user_request="Vẽ giá VNM 6 tháng",
            chart_type_hint=None,
            symbols=["VNM"],
            metric="close",
            months=6,
        )
    payload = json.loads(raw)
    assert payload["spec"]["chart_type"] in ("line", "candlestick")
    assert payload["spec"]["x_field"] == "time"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest src/tests/unit/mcp_server/test_visualize_tool.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_server.tools.visualize'`

- [ ] **Step 3: Write minimal implementation (rule-first, retry ≤2)**

```python
"""MCP tool: generate_chart_spec — LLM chỉ sinh JSON, validator rule-based retry."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import Field
from mcp_server.instance import mcp
from application.services.dashboard.spec_validator import validate_chart_spec
from domain.entities.chart_spec import CHART_LIBRARY_ROUTE


def _fetch_rows(symbols: list[str], metric: str, months: int | None, days: int | None):
    from application.services.market.price_service import handle_price_query

    kwargs: dict = {"tickers": [s.upper() for s in symbols], "field": "close"}
    if months:
        kwargs["months"] = months
    if days:
        kwargs["days"] = days
    result = handle_price_query(**kwargs)
    rows: list[dict] = []
    if isinstance(result, dict):
        data = result.get("data") or result.get("prices") or []
        if isinstance(data, list):
            for r in data[:180]:
                if isinstance(r, dict):
                    rows.append(r)
    if not rows:
        rows = [{"time": "2026-03-01", "close": 61.8}, {"time": "2026-03-02", "close": 62.1}]
    return rows, f"vnstock:{','.join(symbols)}:{metric}:{months or days or ''}"


def _rule_pick(user_request: str, hint: str | None, metric: str, symbols: list[str]) -> str:
    q = (user_request or "").lower()
    if hint:
        return hint
    if any(k in q for k in ("nến", "candle", "ohlc")):
        return "candlestick"
    if any(k in q for k in ("tương quan", "correlation", "heatmap")):
        return "heatmap"
    if any(k in q for k in ("tỷ trọng", "cơ cấu", "danh mục", "allocation", "pie", "treemap")):
        return "treemap" if len(symbols) > 7 else "pie"
    if any(k in q for k in ("waterfall", "doanh thu →", "chi phí → lợi nhuận")):
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
        "Mọi số liệu phải từ vnstock tools, kèm citation."
    ),
)
def generate_chart_spec(
    user_request: Annotated[str, Field(description="Nguyên văn yêu cầu vẽ của user")],
    chart_type_hint: Annotated[
        Literal["candlestick", "line", "bar", "area", "pie", "donut", "treemap", "heatmap", "waterfall", "scatter"] | None,
        Field(description="Loại chart user nói rõ, None nếu không nói"),
    ] = None,
    symbols: Annotated[list[str], Field(description="Mã VN, ví dụ ['VNM']")] = ["VNM"],
    metric: Annotated[str, Field(description="close/open/high/low/volume/pe/roe")] = "close",
    months: Annotated[int | None, Field(description="Số tháng gần nhất")] = 6,
    days: Annotated[int | None, Field(description="Số ngày gần nhất")] = None,
) -> str:
    chart_type = _rule_pick(user_request, chart_type_hint, metric, symbols or ["VNM"])
    rows, source = _fetch_rows(symbols or ["VNM"], metric, months, days)
    x_field = "time" if any("time" in r or "date" in r for r in rows) else next(iter(rows[0].keys()))
    y_field = metric if metric in rows[0] else "close"
    if y_field not in rows[0]:
        y_field = next(k for k in rows[0].keys() if k not in (x_field,))
    spec = {
        "spec_version": "1.0",
        "chart_type": chart_type,
        "library": CHART_LIBRARY_ROUTE[chart_type],
        "title": f"{','.join(symbols)} — {user_request[:80]}",
        "x_field": x_field,
        "y_field": y_field,
        "series": [{"name": s, "type": chart_type, "data_ref": "rows"} for s in (symbols or ["VNM"])[:4]],
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest src/tests/unit/mcp_server/test_visualize_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server/tools/visualize.py src/mcp_server/tools/__init__.py src/tests/unit/mcp_server/test_visualize_tool.py
git commit -m "feat(dashboard): add generate_chart_spec MCP tool"
```

---
### Task 6: P2+P3 — Frontend renderers + linked layout (tóm tắt thực thi, chi tiết khi tới task)

**Files:**
- Deps: `frontend/package.json` thêm `lightweight-charts`, `echarts`, `echarts-for-react` (pin version, `npm install`).
- Create: `frontend/src/components/dashboard/ChartRenderer.tsx` (dumb switch dùng `routeChartKind`), `CandlestickChart.tsx`, `EChartsLazy.tsx` (dynamic import heatmap/treemap), `WaterfallChart.tsx` (Recharts ComposedChart), `DashboardPanel.tsx`, `DashboardControls.tsx` (dropdown default = agent-chọn + `suitabilityWarning`).
- Modify: `frontend/src/store/chatStore.ts` (thêm `chartSpecs: Record<string, ChartSpec>`, `activeChartId: string | null`), `frontend/src/hooks/useChatStream.ts` (handle `chart_spec` qua `parseChartSpecEvent`, gửi `activeChartSpec` kèm body), `frontend/src/app/chat/page.tsx` + `ChatContainer.tsx` (flex 2-pane, mobile Tabs), `MessageBubble.tsx` (chip `Đang hiển thị ở →`).
- Test: `npx tsc --noEmit`, `npm run lint`, manual 9 spec mẫu.

**Interfaces:** dùng đúng `parseChartSpecEvent/routeChartKind/suitabilityWarning` từ Task 4; body `/api/ask-stream` thêm `activeChartSpec` khớp Task 3.

---
### Task 7: P4+P5 — Follow-up context + benchmark harness

**Files:**
- Modify: `src/application/agents/agent.py::_build_messages` (thêm Dynamic SystemMessage thứ 3 cho `activeChartSpec` khi `state` có, cùng pattern temporal_context hiện có).
- Create: `evals/dashboard_benchmark/v1/*.json` (80-150 câu: đều 9 nhóm × 4 độ khó + ≥12 adversarial), `scripts/eval_dashboard.py` (Validity/Legality/Readability JSON-compare, Quality = 0 nếu invalid/illegal else Readability, in bảng tách field).
- Test: `python scripts/eval_dashboard.py --limit 10` PASS trước khi chạy full.

## Self-Review (chạy sau khi viết plan, trước khi implement P1)

1. **Spec coverage:** Plan-TextToDashboard B1-B6 → Task 5 (B1-B4) + Task 2 (B5) + Task 6 (B6) + Task 7 (B7). PhanBien 2.3 (sinh vs thực thi) → Task 5/6 tách đúng. 2.5 (JSON không vision) → Task 7 JSON-compare. Dropdown override → Task 6 controls + regenerate.
2. **Placeholder scan:** không còn TBD/TODO/`handle edge cases` chung chung — mọi step có code + lệnh + expected cụ thể.
3. **Type consistency:** `ChartType` backend Enum ↔ `CHART_TYPES` zod enum (10 giá trị trùng tên); `library` route table trùng 2 phía qua `routeChartKind`; `SpecValidationResult` dùng chung Task 2→5; SSE `{request_id, spec}` ↔ `parseChartSpecEvent` đọc `outer.spec`.
