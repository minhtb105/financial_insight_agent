"""ChartSpec v1.0 — contract duy nhất giữa LLM, validator, SSE và frontend."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ChartType(StrEnum):
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
