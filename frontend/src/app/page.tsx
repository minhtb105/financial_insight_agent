import Link from "next/link"
import { getServerSession } from "next-auth"
import { authOptions } from "@/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MessageCircle, LayoutDashboard, ShieldCheck, TrendingUp } from "lucide-react"

export default async function HomePage() {
  const session = await getServerSession(authOptions)

  return (
    <div className="flex flex-col">
      <section className="container mx-auto px-4 py-12 md:py-20">
        <div className="mx-auto max-w-3xl text-center">
          <Badge variant="secondary" className="mb-4">Giáo dục tài chính có trích dẫn</Badge>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Financial Insight Agent</h1>
          <p className="mt-4 text-lg text-muted-foreground">Trợ lý AI phân tích chứng khoán Việt Nam với LangGraph ReAct — 12 tools, streaming SSE, guardrails & tracing. Dành cho nhà đầu tư muốn quyết định có căn cứ.</p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            {session ? (
              <>
                <Link href="/chat"><Button size="lg"><MessageCircle className="mr-2 h-4 w-4" /> Bắt đầu trò chuyện</Button></Link>
                <Link href="/dashboard"><Button size="lg" variant="outline"><LayoutDashboard className="mr-2 h-4 w-4" /> Xem Dashboard</Button></Link>
              </>
            ) : (
              <>
                <Link href="/login"><Button size="lg">Đăng nhập để bắt đầu</Button></Link>
                <Link href="/login"><Button size="lg" variant="outline">Dùng tài khoản demo</Button></Link>
              </>
            )}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">demo@finsight.vn / demo123 — Mọi câu trả lời chỉ mang tính giáo dục, không phải lời khuyên đầu tư.</p>
        </div>

        <div className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><MessageCircle className="h-4 w-4" /> Chat streaming</CardTitle><CardDescription>12 loại truy vấn: giá, SMA/RSI, so sánh, xếp hạng, danh mục, cảnh báo, dự báo, phân tích ngành</CardDescription></CardHeader>
          </Card>
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="h-4 w-4" /> Dashboard</CardTitle><CardDescription>Bảng giá, biểu đồ SMA/RSI, danh mục mock, phân tích ngành — sẵn sàng nối dữ liệu thực</CardDescription></CardHeader>
          </Card>
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="h-4 w-4" /> Đáng tin cậy</CardTitle><CardDescription>Guardrails, circuit breaker, citation, RAGAS eval — mọi số liệu kèm nguồn để kiểm chứng</CardDescription></CardHeader>
          </Card>
        </div>
      </section>

      <section className="border-t bg-muted/30">
        <div className="container mx-auto px-4 py-8">
          <Card>
            <CardHeader><CardTitle className="text-base">Câu hỏi mẫu</CardTitle></CardHeader>
            <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
              <span>• Giá đóng cửa VCB hôm qua?</span>
              <span>• So sánh khối lượng VIC với HPG trong 1 tuần?</span>
              <span>• Tính SMA9 cho VCB 1 tuần gần nhất</span>
              <span>• Hiệu suất ngành ngân hàng tuần này?</span>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  )
}
