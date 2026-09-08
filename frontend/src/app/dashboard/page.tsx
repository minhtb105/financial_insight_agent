import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/auth"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PriceTable } from "@/components/dashboard/PriceTable"
import { PriceChart, RSIChart } from "@/components/dashboard/PriceChart"
import { PortfolioCard } from "@/components/dashboard/PortfolioCard"
import { SectorView } from "@/components/dashboard/SectorView"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect("/login")

  return (
    <div className="container mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Tổng quan thị trường — dữ liệu mock, sẵn sàng nối FastAPI tools</p>
      </div>

      <Tabs defaultValue="price" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="price">Bảng giá</TabsTrigger>
          <TabsTrigger value="chart">Biểu đồ</TabsTrigger>
          <TabsTrigger value="portfolio">Danh mục</TabsTrigger>
          <TabsTrigger value="sector">Ngành</TabsTrigger>
        </TabsList>

        <TabsContent value="price" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Bảng giá</CardTitle>
              <CardDescription>Giá, khối lượng, SMA9, RSI14 — 6 mã tiêu biểu</CardDescription>
            </CardHeader>
            <CardContent className="p-0 sm:p-6">
              <PriceTable />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="chart" className="space-y-4">
          <PriceChart />
          <RSIChart />
          <Card>
            <CardContent className="p-4 text-sm text-muted-foreground">
              Sau khi nối backend, thay <code>MOCK_CANDLES</code> bằng kết quả từ <code>calculate_technical_indicator</code> và <code>get_stock_price</code>. Gợi ý: tạo BFF <code>/api/market/candles?ticker=VCB</code> proxy tới VNStockClient.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="portfolio" className="space-y-4">
          <PortfolioCard />
        </TabsContent>

        <TabsContent value="sector" className="space-y-4">
          <SectorView />
        </TabsContent>
      </Tabs>
    </div>
  )
}
