"use client"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { MOCK_PRICES } from "@/lib/mock-data"
import { TrendingUp, TrendingDown } from "lucide-react"

export function PriceTable() {
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
          {MOCK_PRICES.map((r) => (
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
              <TableCell className="text-right">{r.sma9?.toLocaleString("vi-VN")}</TableCell>
              <TableCell className="text-right">
                <span className={r.rsi14! > 70 ? "text-red-600 font-semibold" : r.rsi14! < 30 ? "text-green-600 font-semibold" : ""}>{r.rsi14}</span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <p className="p-3 text-xs text-muted-foreground">Dữ liệu mock — kết nối FastAPI `get_stock_price` để thay bằng dữ liệu thực qua BFF.</p>
    </div>
  )
}
