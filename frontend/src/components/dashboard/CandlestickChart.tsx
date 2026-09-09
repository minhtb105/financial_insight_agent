"use client"
import { useEffect, useRef } from "react"
import type { ChartSpec } from "@/lib/chart-spec"

type OhlcRow = { time: string; open: number; high: number; low: number; close: number }

function toNum(v: unknown): number | null {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

/** Candlestick qua TradingView Lightweight Charts v5 (attribution giữ mặc định theo license Apache 2.0). */
export function CandlestickChart({ spec }: { spec: ChartSpec }) {
  const ref = useRef<HTMLDivElement>(null)
  const rows = spec.data as Array<Record<string, unknown>>
  const ohlc: OhlcRow[] = []
  for (const r of rows) {
    const open = toNum(r.open)
    const high = toNum(r.high)
    const low = toNum(r.low)
    const close = toNum(r.close)
    const time = typeof r.time === "string" ? r.time : null
    if (time && open !== null && high !== null && low !== null && close !== null) {
      ohlc.push({ time, open, high, low, close })
    }
  }

  useEffect(() => {
    if (!ref.current || ohlc.length === 0) return
    let chart: { remove: () => void } | null = null
    let disposed = false
    ;(async () => {
      const mod = await import("lightweight-charts")
      if (disposed || !ref.current) return
      const el = ref.current
      // v5: createChart(el, {...}) + addSeries(CandlestickSeries); v4 fallback: addCandlestickSeries
      const c = (
        mod as unknown as {
          createChart: (el: HTMLElement, opts: Record<string, unknown>) => {
            addSeries?: (def: unknown, opts: Record<string, unknown>) => { setData: (d: unknown) => void }
            addCandlestickSeries?: (opts: Record<string, unknown>) => { setData: (d: unknown) => void }
            remove: () => void
            applyOptions?: (opts: Record<string, unknown>) => void
          }
          CandlestickSeries?: unknown
        }
      ).createChart(el, {
        height: 380,
        autoSize: true,
        layout: { attributionLogo: true },
        timeScale: { timeVisible: true },
      })
      const series =
        typeof c.addSeries === "function" && mod.CandlestickSeries
          ? c.addSeries(mod.CandlestickSeries, { upColor: "#16a34a", downColor: "#dc2626" })
          : c.addCandlestickSeries?.({ upColor: "#16a34a", downColor: "#dc2626" })
      series?.setData(ohlc)
      if (!disposed) chart = c
      else c.remove()
    })().catch(() => {})
    return () => {
      disposed = true
      chart?.remove()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-render khi spec đổi
  }, [spec])

  if (ohlc.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Dữ liệu thiếu OHLC (open/high/low/close) nên không vẽ nến được — hãy chọn line hoặc bar.
      </p>
    )
  }
  return <div ref={ref} className="h-[380px] w-full" />
}
