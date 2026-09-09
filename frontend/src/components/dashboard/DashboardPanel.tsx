"use client"
import { BarChart3 } from "lucide-react"
import { useChatStore } from "@/store/chatStore"
import { ChartRenderer } from "./ChartRenderer"
import { DashboardControls } from "./DashboardControls"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/** Panel ngoài khung chat: auto-render spec mới nhất, giữ lịch sử v1..vn, hỏi tiếp không mất chart. */
export function DashboardPanel() {
  const chartSpecs = useChatStore((s) => s.chartSpecs)
  const activeChartId = useChatStore((s) => s.activeChartId)
  const setActiveChart = useChatStore((s) => s.setActiveChart)
  const active = chartSpecs.find((c) => c.id === activeChartId) ?? chartSpecs[chartSpecs.length - 1]

  if (chartSpecs.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <BarChart3 className="h-6 w-6 text-primary" />
        </div>
        <p className="text-sm font-medium">Chưa có biểu đồ</p>
        <p className="max-w-xs text-xs text-muted-foreground">
          Hãy hỏi, ví dụ “Vẽ giá VNM 6 tháng” — biểu đồ sẽ hiện ở đây, to và tương tác được, trong khi
          bạn vẫn hỏi tiếp ở khung chat.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      {chartSpecs.length > 1 && (
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Lịch sử biểu đồ">
          {chartSpecs.map((c, i) => (
            <Button
              key={c.id}
              size="sm"
              role="tab"
              aria-selected={c.id === active?.id}
              variant={c.id === active?.id ? "default" : "outline"}
              className={cn("h-7 px-2 text-xs")}
              onClick={() => setActiveChart(c.id)}
              title={c.spec.title}
            >
              v{i + 1} {c.spec.chart_type}
            </Button>
          ))}
        </div>
      )}
      {active && (
        <>
          <ChartRenderer spec={active.spec} />
          <DashboardControls chartId={active.id} />
        </>
      )}
    </div>
  )
}
