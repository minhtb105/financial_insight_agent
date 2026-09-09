"use client"
import ReactECharts from "echarts-for-react"
import type { ChartSpec } from "@/lib/chart-spec"

function toNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

/** Treemap: mỗi row là 1 leaf (name = x_field, value = y_field), cap 50 leaf. */
export function TreemapChart({ spec }: { spec: ChartSpec }) {
  const rows = spec.data as Array<Record<string, unknown>>
  const leaves = rows.slice(0, 50).map((r) => ({
    name: String(r[spec.x_field] ?? "?"),
    value: Math.abs(toNum(r[spec.y_field])),
  }))
  const option = {
    tooltip: {},
    series: [
      {
        type: "treemap",
        data: leaves,
        label: { show: true, formatter: "{b}" },
        upperLabel: { show: false },
      },
    ],
  }
  return <ReactECharts option={option} style={{ height: 420 }} notMerge lazyUpdate />
}
