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
