"use client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MOCK_PORTFOLIO } from "@/lib/mock-data"

export function PortfolioCard() {
  const totalCost = MOCK_PORTFOLIO.reduce((s, p) => s + p.qty * p.avgPrice, 0)
  const totalValue = MOCK_PORTFOLIO.reduce((s, p) => s + p.qty * p.currentPrice, 0)
  const totalPnL = totalValue - totalCost
  const totalPct = (totalPnL / totalCost) * 100

  return (
    <Card>
      <CardHeader>
        <CardTitle>Danh mục mock</CardTitle>
        <CardDescription>Tổng giá trị: {totalValue.toLocaleString("vi-VN")} ₫ • Lãi/lỗ: <span className={totalPnL >= 0 ? "text-green-600" : "text-red-600"}>{totalPnL.toLocaleString("vi-VN")} ₫ ({totalPct.toFixed(2)}%)</span></CardDescription>
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
            {MOCK_PORTFOLIO.map((p) => {
              const pnl = (p.currentPrice - p.avgPrice) * p.qty
              const pct = ((p.currentPrice - p.avgPrice) / p.avgPrice) * 100
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
        <p className="mt-3 text-xs text-muted-foreground">Mock theo <code>user_portfolio_default.json</code> — sau này nối với tool <code>manage_portfolio</code>.</p>
      </CardContent>
    </Card>
  )
}
