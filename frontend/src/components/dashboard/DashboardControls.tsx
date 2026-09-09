"use client"
import { useState } from "react"
import { CHART_TYPES, suitabilityWarning, type ChartType } from "@/lib/chart-spec"
import { useChatStore } from "@/store/chatStore"
import { useChatStream } from "@/hooks/useChatStream"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const CHART_LABELS: Record<ChartType, string> = {
  candlestick: "Nến",
  line: "Đường",
  bar: "Cột",
  area: "Vùng",
  pie: "Tròn",
  donut: "Vành",
  treemap: "Treemap",
  heatmap: "Heatmap",
  waterfall: "Waterfall",
  scatter: "Scatter",
}

/** Đổi loại biểu đồ local (instant, giữ data) + vẽ lại theo mã/khung mới (qua chat). */
export function DashboardControls({ chartId }: { chartId: string }) {
  const chart = useChatStore((s) => s.chartSpecs.find((c) => c.id === chartId))
  const overrideChartType = useChatStore((s) => s.overrideChartType)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const { send } = useChatStream()
  const [ticker, setTicker] = useState("")
  const [range, setRange] = useState("6 tháng")

  if (!chart) return null
  const warn = suitabilityWarning(chart.spec.chart_type, chart.spec.data.length, chart.spec.series.length)

  const handleRedraw = () => {
    const q = `Vẽ biểu đồ ${CHART_LABELS[chart.spec.chart_type].toLowerCase()} ${ticker.trim() || "VNM"} ${range}`.trim()
    if (!isStreaming) void send(q)
  }

  return (
    <div className="space-y-2 border-t pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="chart-type-select" className="text-xs font-medium text-muted-foreground">
          Loại biểu đồ
        </label>
        <select
          id="chart-type-select"
          value={chart.spec.chart_type}
          onChange={(e) => overrideChartType(chartId, e.target.value as ChartType)}
          className="h-8 rounded border bg-background px-2 text-sm"
        >
          {CHART_TYPES.map((t) => (
            <option key={t} value={t}>
              {CHART_LABELS[t]}
              {t === chart.spec.chart_type ? " ✓" : ""}
            </option>
          ))}
        </select>
        {warn && (
          <Badge variant="secondary" className="text-xs">
            {warn}
          </Badge>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="Mã, vd VNM"
          maxLength={8}
          className="h-8 w-28 rounded border bg-background px-2 text-sm"
          aria-label="Mã chứng khoán"
        />
        <select
          value={range}
          onChange={(e) => setRange(e.target.value)}
          className="h-8 rounded border bg-background px-2 text-sm"
          aria-label="Khung thời gian"
        >
          {["1 tháng", "3 tháng", "6 tháng", "1 năm"].map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <Button size="sm" variant="outline" onClick={handleRedraw} disabled={isStreaming}>
          Vẽ lại
        </Button>
      </div>
    </div>
  )
}
