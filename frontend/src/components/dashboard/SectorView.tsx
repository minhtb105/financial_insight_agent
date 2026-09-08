"use client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MOCK_SECTORS } from "@/lib/mock-data"

export function SectorView() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Phân tích ngành</CardTitle>
        <CardDescription>Hiệu suất theo ngành (mock, sẽ nối `analyze_sector`)</CardDescription>
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
            {MOCK_SECTORS.map((s) => (
              <TableRow key={s.sector}>
                <TableCell className="font-medium">{s.sector}</TableCell>
                <TableCell className="text-right">
                  <Badge variant={s.changePct >= 0 ? "default" : "destructive"} className={s.changePct >= 0 ? "bg-green-600" : ""}>{s.changePct > 0 ? "+" : ""}{s.changePct.toFixed(1)}%</Badge>
                </TableCell>
                <TableCell className="text-right">{s.volume}</TableCell>
                <TableCell><Badge variant="secondary">{s.topTicker}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
