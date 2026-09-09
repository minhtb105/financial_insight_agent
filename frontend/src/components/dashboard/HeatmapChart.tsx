"use client"
import ReactECharts from "echarts-for-react"
import type { ChartSpec } from "@/lib/chart-spec"

function toNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

/** Heatmap thời gian × series từ y_field. Single-series vẫn vẽ được (1 hàng). */
export function HeatmapChart({ spec }: { spec: ChartSpec }) {
  const rows = spec.data as Array<Record<string, unknown>>
  const MAX_T = 30
  const sampled = rows.length > MAX_T ? rows.filter((_, i) => i % Math.ceil(rows.length / MAX_T) === 0) : rows
  const times = sampled.map((r) => String(r[spec.x_field] ?? ""))
  const seriesNames = spec.series.map((s) => s.name)
  const data: Array<[number, number, number]> = []
  sampled.forEach((r, yi) => {
    seriesNames.forEach((_, xi) => {
      data.push([xi, yi, toNum(r[spec.y_field])])
    })
  })
  const values = data.map((d) => d[2])
  const option = {
    tooltip: { position: "top" },
    grid: { height: "60%", top: "10%" },
    xAxis: { type: "category", data: seriesNames, splitArea: { show: true } },
    yAxis: { type: "category", data: times, splitArea: { show: true } },
    visualMap: {
      min: Math.min(...values, 0),
      max: Math.max(...values, 1),
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
    },
    series: [{ type: "heatmap", data, label: { show: false } }],
  }
  return <ReactECharts option={option} style={{ height: 420 }} notMerge lazyUpdate />
}
