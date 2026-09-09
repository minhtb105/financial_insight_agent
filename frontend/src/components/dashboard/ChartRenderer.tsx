"use client"
import dynamic from "next/dynamic"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { chartSpecSchema, routeChartKind, suitabilityWarning } from "@/lib/chart-spec"
import { RechartsGeneric } from "./RechartsGeneric"
import { CandlestickChart } from "./CandlestickChart"
import { WaterfallChart } from "./WaterfallChart"

const HeatmapChart = dynamic(() => import("./HeatmapChart").then((m) => m.HeatmapChart), {
  ssr: false,
  loading: () => <p className="text-sm text-muted-foreground">Đang tải heatmap…</p>,
})
const TreemapChart = dynamic(() => import("./TreemapChart").then((m) => m.TreemapChart), {
  ssr: false,
  loading: () => <p className="text-sm text-muted-foreground">Đang tải treemap…</p>,
})

/** Dumb router: chart_type → đúng thư viện, không suy luận ở frontend. */
export function ChartRenderer({ spec: raw }: { spec: unknown }) {
  const parsed = chartSpecSchema.safeParse(raw)
  if (!parsed.success) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Spec không hợp lệ</CardTitle>
          <CardDescription>Validator từ chối chart-spec này — hệ thống sẽ thử lại.</CardDescription>
        </CardHeader>
      </Card>
    )
  }
  const spec = parsed.data
  const kind = routeChartKind(spec.chart_type)
  const warning = suitabilityWarning(spec.chart_type, spec.data.length, spec.series.length)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{spec.title}</CardTitle>
        <CardDescription>
          {spec.data_source} • {spec.data.length} điểm • {spec.library}
        </CardDescription>
        {warning && (
          <div className="flex flex-wrap gap-1">
            <Badge variant="secondary" className="text-xs">
              {warning}
            </Badge>
          </div>
        )}
      </CardHeader>
      <CardContent className="h-[420px]">
        {kind === "tradingview" ? (
          <CandlestickChart spec={spec} />
        ) : kind === "echarts" ? (
          spec.chart_type === "heatmap" ? (
            <HeatmapChart spec={spec} />
          ) : (
            <TreemapChart spec={spec} />
          )
        ) : spec.chart_type === "waterfall" ? (
          <WaterfallChart spec={spec} />
        ) : (
          <RechartsGeneric spec={spec} />
        )}
        <p className="mt-2 text-xs text-muted-foreground">
          Thông tin chỉ mang tính giáo dục, không phải lời khuyên đầu tư.
        </p>
      </CardContent>
    </Card>
  )
}
