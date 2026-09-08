"use client"
import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { MOCK_CANDLES } from "@/lib/mock-data"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts"
import { useCandles } from "@/hooks/useMarketData"

const TICKER_OPTIONS = ["VCB", "FPT", "VNM", "HPG", "VIC", "MWG"]

export function PriceChart({ ticker: initial = "VCB" }: { ticker?: string }) {
  const [ticker, setTicker] = useState(initial)
  const { data, loading, error } = useCandles(ticker, 30)
  const chartData = data?.candles?.length ? data.candles : MOCK_CANDLES

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Biểu đồ giá & SMA9</CardTitle>
          <CardDescription>
            {ticker} — 30 ngày gần nhất {loading ? "(đang tải…)" : error ? `(lỗi)` : data?.candles?.length ? "(dữ liệu thực)" : "(mock)"}
          </CardDescription>
        </div>
        <select value={ticker} onChange={(e) => setTicker(e.target.value)} className="h-8 rounded border bg-background px-2 text-sm">
          {TICKER_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </CardHeader>
      <CardContent className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData as never}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={4} />
            <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="price" name="Giá" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="sma9" name="SMA9" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

export function RSIChart({ ticker = "VCB" }: { ticker?: string }) {
  const { data, loading, error } = useCandles(ticker, 30)
  const chartData = data?.candles?.length ? data.candles : MOCK_CANDLES
  return (
    <Card>
      <CardHeader>
        <CardTitle>RSI14</CardTitle>
        <CardDescription>
          {ticker} — Vùng quá mua {">"}70, quá bán {"<"}30 {loading ? "(đang tải…)" : error ? "(lỗi)" : data?.candles?.length ? "(thực)" : "(mock)"}
        </CardDescription>
      </CardHeader>
      <CardContent className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData as never}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={4} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="rsi" name="RSI14" stroke="#8b5cf6" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

// Combined TechChart for future use (deduped)
export function TechChart({ ticker = "VCB", kind = "price" }: { ticker?: string; kind?: "price" | "rsi" }) {
  return kind === "rsi" ? <RSIChart ticker={ticker} /> : <PriceChart ticker={ticker} />
}
