"use client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MOCK_PORTFOLIO } from "@/lib/mock-data"
import { usePortfolio } from "@/hooks/useMarketData"

export function PortfolioCard() {
  const { data, loading, error } = usePortfolio()

  // Derive holdings from real data if available
  const isLive = data && typeof data === "object" && (("portfolio_value" in data && (data as Record<string, unknown>).portfolio_value) || ("holdings" in data))
  const holdings = (() => {
    if (data && typeof data === "object") {
      // portfolio_summary shape: { portfolio_value: { holdings: {...}, portfolio_value: number }, ... } or direct holdings
      const d = data as Record<string, unknown>
      const pv = (d.portfolio_value as Record<string, unknown>) ?? d
      const h = (pv.holdings as Record<string, { quantity: number; current_price: number; value: number }>) ?? null
      if (h && Object.keys(h).length) {
        return Object.entries(h).map(([ticker, v]) => ({
          ticker,
          qty: v.quantity,
          avgPrice: v.current_price, // no avgPrice in real; approximate
          currentPrice: v.current_price,
        }))
      }
      // fallback to direct holdings if shape is holdings dict
      if (d.holdings && typeof d.holdings === "object") {
        const hh = d.holdings as Record<string, unknown>
        if (Object.keys(hh).length) {
          return Object.entries(hh).map(([ticker, v]) => {
            const vv = v as Record<string, unknown>
            return { ticker, qty: (vv.quantity as number) ?? 0, avgPrice: (vv.current_price as number) ?? 0, currentPrice: (vv.current_price as number) ?? 0 }
          })
        }
      }
    }
    return null
  })()

  const display = holdings ?? MOCK_PORTFOLIO
  const totalCost = display.reduce((s, p) => s + p.qty * p.avgPrice, 0)
  const totalValue = display.reduce((s, p) => s + p.qty * p.currentPrice, 0)
  const totalPnL = totalValue - totalCost
  const totalPct = totalCost ? (totalPnL / totalCost) * 100 : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isLive ? "Danh mục" : "Danh mục mock"}</CardTitle>
        <CardDescription>
          Tổng giá trị: {totalValue.toLocaleString("vi-VN")} ₫ • Lãi/lỗ: <span className={totalPnL >= 0 ? "text-green-600" : "text-red-600"}>{totalPnL.toLocaleString("vi-VN")} ₫ ({totalPct.toFixed(2)}%)</span>
          {loading ? " (đang tải…)" : error ? " (lỗi, dùng mock)" : isLive ? " (dữ liệu thực)" : " (mock)"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mã</TableHead>
              <TableHead className="text-right">Số lượng</TableHead>
              <TableHead className="text-right">Giá TB</TableHead>
              <TableHead className="text-right">Giá hiện tại</TableHead>
              <TableHead className="text-right">Lãi/lỗ</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {display.map((p) => {
              const pnl = (p.currentPrice - p.avgPrice) * p.qty
              const pct = p.avgPrice ? ((p.currentPrice - p.avgPrice) / p.avgPrice) * 100 : 0
              return (
                <TableRow key={p.ticker}>
                  <TableCell className="font-medium">{p.ticker}</TableCell>
                  <TableCell className="text-right">{p.qty}</TableCell>
                  <TableCell className="text-right">{p.avgPrice.toLocaleString("vi-VN")}</TableCell>
                  <TableCell className="text-right">{p.currentPrice.toLocaleString("vi-VN")}</TableCell>
                  <TableCell className={`text-right ${pnl >= 0 ? "text-green-600" : "text-red-600"}`}>{pnl.toLocaleString("vi-VN")} ({pct.toFixed(1)}%)</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        <p className="mt-3 text-xs text-muted-foreground">
          {isLive ? "Dữ liệu thực từ BFF /api/market/portfolio" : "Mock theo user_portfolio_default.json — đã nối BFF, fallback khi backend chưa sẵn sàng."}
        </p>
      </CardContent>
    </Card>
  )
}
