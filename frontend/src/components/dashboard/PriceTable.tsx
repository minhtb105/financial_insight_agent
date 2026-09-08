"use client"
import { useMemo, useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { MOCK_PRICES, type PriceRow } from "@/lib/mock-data"
import { TrendingUp, TrendingDown } from "lucide-react"
import { usePrices } from "@/hooks/useMarketData"

const DEFAULT_TICKERS = ["VCB", "FPT", "VNM", "HPG", "VIC", "MWG"]

function deriveRows(raw: Record<string, unknown> | null): PriceRow[] | null {
  if (!raw) return null
  const rows: PriceRow[] = []
  for (const ticker of DEFAULT_TICKERS) {
    const entry = raw[ticker] as unknown as { data?: Array<Record<string, unknown>>; error?: string } | undefined
    if (!entry || entry.error || !Array.isArray(entry.data) || entry.data.length === 0) continue
    const data = entry.data
    const last = data[data.length - 1] as Record<string, unknown>
    const prev = data.length > 1 ? (data[data.length - 2] as Record<string, unknown>) : last
    const price = (last.close as number) ?? (last.price as number) ?? 0
    const prevPrice = (prev.close as number) ?? (prev.price as number) ?? price
    const change = price - prevPrice
    const changePct = prevPrice ? (change / prevPrice) * 100 : 0
    const volume = (last.volume as number) ?? 0
    rows.push({ ticker, price, change, changePct, volume })
  }
  return rows.length ? rows : null
}

export function PriceTable() {
  const [tickers] = useState(DEFAULT_TICKERS)
  const { data, loading, error } = usePrices(tickers, "close", 30)
  const liveRows = useMemo(() => deriveRows(data as Record<string, unknown> | null), [data])
  const rows = liveRows ?? MOCK_PRICES
  const isLive = !!liveRows

  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Mã</TableHead>
            <TableHead className="text-right">Giá</TableHead>
            <TableHead className="text-right">Thay đổi</TableHead>
            <TableHead className="text-right">% Thay đổi</TableHead>
            <TableHead className="text-right">Khối lượng</TableHead>
            <TableHead className="text-right">SMA9</TableHead>
            <TableHead className="text-right">RSI14</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.ticker}>
              <TableCell className="font-medium">{r.ticker}</TableCell>
              <TableCell className="text-right">{r.price.toLocaleString("vi-VN")} ₫</TableCell>
              <TableCell className={`text-right flex items-center justify-end gap-1 ${r.change >= 0 ? "text-green-600" : "text-red-600"}`}>
                {r.change >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {r.change > 0 ? "+" : ""}{r.change.toLocaleString("vi-VN")}
              </TableCell>
              <TableCell className={`text-right ${r.changePct >= 0 ? "text-green-600" : "text-red-600"}`}>
                <Badge variant={r.changePct >= 0 ? "default" : "destructive"} className={r.changePct >= 0 ? "bg-green-600" : ""}>{r.changePct > 0 ? "+" : ""}{r.changePct.toFixed(2)}%</Badge>
              </TableCell>
              <TableCell className="text-right">{r.volume.toLocaleString("vi-VN")}</TableCell>
              <TableCell className="text-right">{r.sma9?.toLocaleString("vi-VN") ?? "—"}</TableCell>
              <TableCell className="text-right">
                <span className={r.rsi14! > 70 ? "text-red-600 font-semibold" : r.rsi14! < 30 ? "text-green-600 font-semibold" : ""}>{r.rsi14 ?? "—"}</span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="p-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {loading ? "Đang tải dữ liệu thực..." : isLive ? "Dữ liệu thực từ BFF /api/market/prices" : "Dữ liệu mock — backend chưa sẵn sàng hoặc lỗi mạng"}
        </span>
        {error && <span className="text-amber-600">Lỗi: {error.slice(0, 80)}</span>}
      </div>
    </div>
  )
}
