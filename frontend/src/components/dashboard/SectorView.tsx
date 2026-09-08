"use client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MOCK_SECTORS } from "@/lib/mock-data"
import { useSectors } from "@/hooks/useMarketData"

export function SectorView() {
  const { data, loading, error } = useSectors("1w")
  const rows = data?.sectors?.length ? data.sectors : MOCK_SECTORS
  const isLive = !!data?.sectors?.length

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phân tích ngành</CardTitle>
        <CardDescription>
          Hiệu suất theo ngành {loading ? "(đang tải…)" : error ? "(lỗi, dùng mock)" : isLive ? "(dữ liệu thực 1w)" : "(mock, đã nối analyze_sector)"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ngành</TableHead>
              <TableHead className="text-right">% Thay đổi</TableHead>
              <TableHead className="text-right">Khối lượng</TableHead>
              <TableHead>Mã tiêu biểu</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((s) => (
              <TableRow key={s.sector}>
                <TableCell className="font-medium">{s.sector}</TableCell>
                <TableCell className="text-right">
                  <Badge variant={s.changePct >= 0 ? "default" : "destructive"} className={s.changePct >= 0 ? "bg-green-600" : ""}>{s.changePct > 0 ? "+" : ""}{s.changePct.toFixed(1)}%</Badge>
                </TableCell>
                <TableCell className="text-right">{(s as unknown as { volume?: string }).volume ?? "—"}</TableCell>
                <TableCell><Badge variant="secondary">{s.topTicker}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {!isLive && !loading && <p className="mt-2 text-xs text-muted-foreground">Đang hiển thị mock — backend chưa sẵn sàng hoặc dữ liệu ngành trống.</p>}
      </CardContent>
    </Card>
  )
}
