import Link from "next/link"
import { getServerSession } from "next-auth"
import { authOptions } from "@/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  MessageCircle,
  LayoutDashboard,
  BookOpen,
  Search,
  Quote,
  ShieldCheck,
  TrendingUp,
  Table2,
  LineChart,
  ArrowRight,
  Check,
  Scale,
} from "lucide-react"

export default async function HomePage() {
  const session = await getServerSession(authOptions)

  return (
    <div className="flex flex-col">
      {/* Hero — 60/40, no kicker above H1, primary action under sub */}
      <section className="border-b">
        <div className="container mx-auto px-4 py-10 md:py-16 lg:py-20">
          <div className="grid gap-8 lg:grid-cols-[1.35fr_0.85fr] lg:gap-10 items-start">
            {/* Left */}
            <div className="min-w-0">
              <h1 className="text-[2.05rem] font-bold tracking-[-0.03em] leading-[1.08] sm:text-5xl lg:text-[3.25rem]">
                Hiểu chứng khoán
                <span className="block text-foreground/90">
                  trước khi quyết định.
                </span>
                <span className="block text-muted-foreground text-[0.62em] font-semibold tracking-tight mt-1">
                  Mọi câu trả lời đều có nguồn để bạn tự kiểm chứng.
                </span>
              </h1>
              <p className="mt-4 max-w-[60ch] text-[15px] leading-7 text-muted-foreground sm:text-[17px]">
                Financial Insight Agent giải thích khái niệm, chỉ báo SMA/RSI và cách đọc dữ
                liệu vnstock bằng tiếng Việt — với trích dẫn rõ nguồn. Chỉ giáo dục, không
                khuyến nghị mua/bán, không quản lý tiền hộ.
              </p>

              <div className="mt-7 flex flex-wrap gap-3">
                {session ? (
                  <>
                    <Link href="/chat">
                      <Button size="lg" className="shadow-[0_1px_0_rgba(0,0,0,0.08),0_8px_24px_rgba(67,56,202,0.18)]">
                        <MessageCircle className="mr-2 h-4 w-4" />
                        Bắt đầu trò chuyện
                        <ArrowRight className="ml-2 h-4 w-4 opacity-70" />
                      </Button>
                    </Link>
                    <Link href="/dashboard">
                      <Button size="lg" variant="outline">
                        <LayoutDashboard className="mr-2 h-4 w-4" />
                        Xem Dashboard minh họa
                      </Button>
                    </Link>
                  </>
                ) : (
                  <>
                    <Link href="/login">
                      <Button size="lg" className="shadow-[0_1px_0_rgba(0,0,0,0.08),0_8px_24px_rgba(67,56,202,0.18)]">
                        Đăng nhập để bắt đầu
                        <ArrowRight className="ml-2 h-4 w-4 opacity-70" />
                      </Button>
                    </Link>
                    <Link href="/login">
                      <Button size="lg" variant="outline">
                        Dùng tài khoản demo
                      </Button>
                    </Link>
                  </>
                )}
              </div>

              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                demo@finsight.vn / demo123 — Chỉ phục vụ giáo dục &amp; thông tin.
                <span className="mx-1.5 opacity-40">·</span>
                Ranh giới UBCKNN: không khuyến nghị cá nhân khi chưa được cấp phép.
              </p>

              {/* Proof strip — inline, not cards */}
              <div className="mt-8 grid grid-cols-3 gap-0 overflow-hidden rounded-xl border bg-card sm:mt-10">
                <div className="px-3 py-4 text-center sm:px-4 sm:py-5">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    Tài khoản cá nhân
                  </div>
                  <div className="mt-1 font-mono text-lg font-semibold tabular-nums tracking-tight sm:text-xl">
                    13,0 tr
                  </div>
                  <div className="mt-1 text-[11px] leading-4 text-muted-foreground">
                    05/2026 · VSDC
                  </div>
                </div>
                <div className="border-l px-3 py-4 text-center sm:px-4 sm:py-5">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    Chưa dùng tư vấn trả phí
                  </div>
                  <div className="mt-1 font-mono text-lg font-semibold tabular-nums tracking-tight sm:text-xl">
                    95%
                  </div>
                  <div className="mt-1 text-[11px] leading-4 text-muted-foreground">
                    TVS 2026 · 1.000 người
                  </div>
                </div>
                <div className="border-l px-3 py-4 text-center sm:px-4 sm:py-5">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    Đã dùng GenAI cho tài chính
                  </div>
                  <div className="mt-1 font-mono text-lg font-semibold tabular-nums tracking-tight sm:text-xl">
                    75%
                  </div>
                  <div className="mt-1 text-[11px] leading-4 text-muted-foreground">
                    Sun Life 2026
                  </div>
                </div>
              </div>

              <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
                Thêm: 59% tự đánh giá kiến thức ở mức cơ bản/thấp; 73% chưa có kế hoạch dài hạn (Sun Life/TVS 2026) · 24% hiểu biết tài chính cơ bản (S&P 2014, ghi rõ năm).
              </p>
            </div>

            {/* Right — dashboard teaser as single card, offset shadow blur, no halo */}
            <div className="min-w-0 lg:sticky lg:top-20">
              <div className="overflow-hidden rounded-xl border bg-card shadow-[0_1px_2px_rgba(0,0,0,0.06),0_12px_32px_rgba(0,0,0,0.08)]">
                <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-3">
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <Table2 className="h-3.5 w-3.5 text-muted-foreground" />
                    Dashboard minh họa
                    <span className="hidden sm:inline font-normal text-muted-foreground">
                      · vnstock · chỉ để giải thích công thức
                    </span>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-[11px] font-medium text-emerald-700 ring-1 ring-emerald-500/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Dữ liệu mẫu
                  </span>
                </div>

                {/* Mini price table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/30 text-left text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                        <th className="px-4 py-2 font-medium">Mã</th>
                        <th className="px-3 py-2 text-right font-medium">Giá</th>
                        <th className="px-3 py-2 text-right font-medium">SMA9</th>
                        <th className="px-3 py-2 text-right font-medium">RSI14</th>
                      </tr>
                    </thead>
                    <tbody className="font-mono text-[13px] tabular-nums">
                      <tr className="border-b">
                        <td className="px-4 py-2.5 font-sans font-medium">VCB</td>
                        <td className="px-3 py-2.5 text-right">92,40</td>
                        <td className="px-3 py-2.5 text-right text-muted-foreground">91,80</td>
                        <td className="px-3 py-2.5 text-right">
                          <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-amber-700 ring-1 ring-amber-500/20">58,2</span>
                        </td>
                      </tr>
                      <tr className="border-b">
                        <td className="px-4 py-2.5 font-sans font-medium">HPG</td>
                        <td className="px-3 py-2.5 text-right">28,15</td>
                        <td className="px-3 py-2.5 text-right text-muted-foreground">27,90</td>
                        <td className="px-3 py-2.5 text-right">
                          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-emerald-700 ring-1 ring-emerald-500/20">62,4</span>
                        </td>
                      </tr>
                      <tr className="border-b">
                        <td className="px-4 py-2.5 font-sans font-medium">VIC</td>
                        <td className="px-3 py-2.5 text-right">45,80</td>
                        <td className="px-3 py-2.5 text-right text-muted-foreground">46,10</td>
                        <td className="px-3 py-2.5 text-right">
                          <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-sky-700 ring-1 ring-sky-500/20">47,9</span>
                        </td>
                      </tr>
                      <tr>
                        <td className="px-4 py-2.5 font-sans font-medium">FPT</td>
                        <td className="px-3 py-2.5 text-right">138,20</td>
                        <td className="px-3 py-2.5 text-right text-muted-foreground">137,40</td>
                        <td className="px-3 py-2.5 text-right">
                          <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-amber-700 ring-1 ring-amber-500/20">55,1</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Mini sparkline — pure SVG, no library, proves content not chrome */}
                <div className="border-t bg-muted/20 px-4 py-3">
                  <div className="mb-2 flex items-center gap-2 text-xs">
                    <LineChart className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-medium">SMA9 minh họa</span>
                    <span className="text-muted-foreground">· VCB 9 phiên · công thức trung bình trượt</span>
                  </div>
                  <svg viewBox="0 0 320 64" className="h-16 w-full" role="img" aria-label="Biểu đồ SMA9 minh họa cho VCB">
                    <rect x="0" y="0" width="320" height="64" rx="8" className="fill-background" />
                    <path
                      d="M8 44 L48 38 L88 42 L128 30 L168 34 L208 22 L248 28 L288 18 L312 20"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.75"
                      className="text-primary"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M8 44 L48 38 L88 42 L128 30 L168 34 L208 22 L248 28 L288 18 L312 20 L312 48 L8 48 Z"
                      className="fill-primary/10"
                    />
                    <g className="fill-primary">
                      <circle cx="312" cy="20" r="3" />
                      <circle cx="312" cy="20" r="7" className="fill-primary/20" />
                    </g>
                    <text x="8" y="62" className="fill-muted-foreground text-[7px]">T-8</text>
                    <text x="304" y="62" className="fill-muted-foreground text-[7px]">T</text>
                  </svg>
                  <p className="mt-2 text-[11px] leading-4 text-muted-foreground">
                    Minh họa công thức, không phải tín hiệu mua/bán. Mở
                    <Link href="/dashboard" className="mx-1 underline decoration-muted-foreground/30 underline-offset-4 hover:decoration-foreground">
                      Dashboard
                    </Link>
                    để xem bảng giá &amp; biểu đồ đầy đủ.
                  </p>
                </div>
              </div>

              <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Quote className="h-3.5 w-3.5" />
                Mọi số trong trả lời Chat đều kèm citation — bạn bấm là thấy nguồn.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works — 3 steps, distinct rhythm, not 3 equal icon-cards */}
      <section className="container mx-auto px-4 py-10 md:py-14">
        <div className="mx-auto max-w-5xl">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">Hỏi tiếng Việt, hiểu có căn cứ</h2>
            <p className="text-sm text-muted-foreground">Ba bước — không vòng vo</p>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {/* Step 01 — larger, with list */}
            <div className="rounded-xl border bg-card p-5 md:col-span-1">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                  01
                </span>
                <span className="text-sm font-semibold">Đặt câu hỏi như bạn nghĩ</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                “SMA là gì?”, “RSI 70 nghĩa là sao?”, “Đọc bảng giá thế nào?”. Không cần đúng thuật ngữ.
              </p>
              <div className="mt-4 rounded-lg border bg-muted/40 p-3">
                <div className="flex items-center gap-2 text-xs font-medium">
                  <Search className="h-3.5 w-3.5 text-muted-foreground" />
                  Ví dụ câu hỏi
                </div>
                <ul className="mt-2 space-y-1.5 text-sm">
                  <li className="flex gap-2">
                    <span className="text-muted-foreground">·</span> SMA9 tính thế nào cho VCB?
                  </li>
                  <li className="flex gap-2">
                    <span className="text-muted-foreground">·</span> RSI khác SMA ở điểm gì?
                  </li>
                </ul>
              </div>
            </div>

            {/* Step 02 — centered emphasis */}
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-foreground text-xs font-semibold text-background">
                  02
                </span>
                <span className="text-sm font-semibold">Nhận giải thích + công thức</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Agent diễn giải bằng tiếng Việt sư phạm, kèm công thức và ý nghĩa — ví dụ SMA là trung bình 9 phiên.
              </p>
              <div className="mt-4 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2.5 ring-1 ring-primary/10">
                <BookOpen className="h-4 w-4 text-primary" />
                <span className="text-sm">
                  SMA<sub>n</sub> = (P<sub>1</sub> + … + P<sub>n</sub>) / n
                </span>
                <span className="ml-auto text-xs text-muted-foreground">n = 9, 20…</span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">Dữ liệu vnstock chỉ để minh họa công thức.</p>
            </div>

            {/* Step 03 — citation focus */}
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border bg-background text-xs font-semibold">
                  03
                </span>
                <span className="text-sm font-semibold">Kiểm chứng ngay trong câu trả lời</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Mọi khái niệm/số liệu đều có trích dẫn bấm được. Thiếu nguồn thì không khẳng định.
              </p>
              <div className="mt-4 rounded-lg border bg-card p-3">
                <div className="text-xs font-medium">RSI &gt; 70 thường được mô tả là “quá mua” trong nhiều giáo trình</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full border bg-muted/50 px-2 py-1 text-[11px]">
                    <Quote className="h-3 w-3" /> Investopedia — RSI
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border bg-muted/50 px-2 py-1 text-[11px]">
                    Sách PTS — Phân tích kỹ thuật
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Sample Q&A — proves citation UX */}
      <section className="border-y bg-muted/30">
        <div className="container mx-auto px-4 py-10 md:py-12">
          <div className="mx-auto max-w-5xl">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4 text-primary" />
              <h2 className="text-base font-semibold tracking-tight">Trả lời mẫu — có trích dẫn</h2>
              <span className="ml-auto hidden text-xs text-muted-foreground sm:inline">
                Bấm citation để mở nguồn · Không phải khuyến nghị
              </span>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Câu hỏi</div>
                  <div className="mt-1 text-sm font-medium">“SMA9 cho VCB tuần này nghĩa là gì?”</div>
                  <div className="mt-4 rounded-lg border bg-muted/40 p-3 text-sm leading-6">
                    SMA9 là trung bình giá đóng cửa 9 phiên gần nhất. Với VCB, SMA9 quanh 91,8 cho thấy xu hướng ngắn hạn — dùng để học cách làm mịn nhiễu, không phải tín hiệu mua/bán.
                    <span className="ml-1 inline-flex translate-y-0.5 gap-1">
                      <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary ring-1 ring-primary/15">
                        [vnstock · VCB]
                      </span>
                      <span className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs font-medium ring-1 ring-border">
                        [Giáo trình · SMA]
                      </span>
                    </span>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    Kèm công thức + bảng giá minh họa
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Câu hỏi</div>
                  <div className="mt-1 text-sm font-medium">“RSI 62 có phải là mua không?”</div>
                  <div className="mt-4 rounded-lg border bg-muted/40 p-3 text-sm leading-6">
                    RSI đo động lượng 0–100. 62 là vùng trung tính hơi mạnh — giáo trình thường lấy 70/30 làm mốc “quá mua/quá bán” để học, không phải lệnh.
                    <span className="ml-1 inline-flex translate-y-0.5">
                      <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary ring-1 ring-primary/15">
                        [Investopedia · RSI]
                      </span>
                    </span>
                    <div className="mt-2 rounded bg-amber-500/10 px-2.5 py-1.5 text-xs leading-5 text-amber-900 ring-1 ring-amber-500/20">
                      Lưu ý: Đây là kiến thức chung, không phải khuyến nghị cho danh mục của bạn. Tự đánh giá rủi ro trước khi quyết định.
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <Link href={session ? "/chat" : "/login"}>
                <Button size="sm">
                  <MessageCircle className="mr-2 h-3.5 w-3.5" />
                  Thử hỏi ngay
                </Button>
              </Link>
              <span className="inline-flex items-center text-xs text-muted-foreground">
                <ShieldCheck className="mr-1.5 h-3.5 w-3.5" />
                Guardrails + disclaimer tự động khi bạn hỏi theo hướng tư vấn cá nhân
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Trust strip — eval harness */}
      <section className="container mx-auto px-4 py-10">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-xl border bg-card p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="flex items-center gap-2 text-sm font-semibold">
                  <Scale className="h-4 w-4 text-primary" />
                  Độ tin cậy đo được — không nói miệng
                </h2>
                <p className="mt-1 max-w-[60ch] text-sm leading-6 text-muted-foreground">
                  Mọi thay đổi nội dung đều được kiểm bằng eval harness sẵn có. Không bịa benchmark khi chưa đo lại sau khi thu hẹp scope giáo dục.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                evals/ · 36 cases
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border bg-muted/30 px-4 py-3">
                <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">citation_rate</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">—</span>
                  <span className="text-xs text-muted-foreground">mục tiêu &gt; 0,95</span>
                </div>
                <div className="mt-1 text-xs leading-4 text-muted-foreground">Mọi khẳng định có số liệu đều kèm nguồn</div>
              </div>
              <div className="rounded-lg border bg-muted/30 px-4 py-3">
                <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">faithfulness (RAGAS)</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">—</span>
                  <span className="text-xs text-muted-foreground">thang 0–5</span>
                </div>
                <div className="mt-1 text-xs leading-4 text-muted-foreground">Trả lời bám nguồn, không suy diễn</div>
              </div>
              <div className="rounded-lg border bg-muted/30 px-4 py-3">
                <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">numeric_match_rate</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">—</span>
                  <span className="text-xs text-muted-foreground">so với vnstock</span>
                </div>
                <div className="mt-1 text-xs leading-4 text-muted-foreground">Số liệu minh họa khớp nguồn</div>
              </div>
            </div>
            <p className="mt-3 text-xs leading-4 text-muted-foreground">
              Dấu “—” nghĩa là chưa đo lại sau khi đổi spec sang chỉ giáo dục — sẽ cập nhật sau khi chạy lại golden dataset.
            </p>
          </div>
        </div>
      </section>

      {/* FAQ — legal boundary */}
      <section className="border-t bg-muted/30">
        <div className="container mx-auto px-4 py-10 md:py-12">
          <div className="mx-auto max-w-5xl">
            <h2 className="text-base font-semibold tracking-tight">Ranh giới rõ ràng — để bạn an tâm</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border bg-card p-5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <Scale className="h-4 w-4" />
                </div>
                <div className="mt-3 text-sm font-semibold">Có khuyến nghị mua/bán không?</div>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                  Không. Chỉ giải thích khái niệm &amp; cách đọc dữ liệu. Hỏi theo hướng “nên mua VCB không?” sẽ được chuyển thành kiến thức chung + disclaimer.
                </p>
              </div>
              <div className="rounded-xl border bg-card p-5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <TrendingUp className="h-4 w-4" />
                </div>
                <div className="mt-3 text-sm font-semibold">Dữ liệu từ đâu?</div>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                  Giá/khối lượng lấy qua vnstock theo thời gian thực để minh họa công thức SMA/RSI. Mỗi số trong Chat đều gắn nguồn bấm được.
                </p>
              </div>
              <div className="rounded-xl border bg-card p-5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <div className="mt-3 text-sm font-semibold">Tôi cần chuẩn bị gì?</div>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                  Không cần. Chỉ cần hỏi bằng tiếng Việt như bạn nghĩ. Tài khoản demo đã có sẵn để thử ngay.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Close CTA */}
      <section className="container mx-auto px-4 py-10">
        <div className="mx-auto max-w-3xl rounded-xl border bg-foreground px-6 py-8 text-center text-background sm:px-8">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">Sẵn sàng hiểu đúng trước khi quyết?</h2>
          <p className="mx-auto mt-2 max-w-[55ch] text-sm leading-6 text-background/70">
            Bắt đầu với một câu hỏi tiếng Việt. Mọi câu trả lời đều kèm nguồn — bạn kiểm chứng được ngay.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link href={session ? "/chat" : "/login"}>
              <Button size="lg" variant="secondary" className="bg-background text-foreground hover:bg-background/90">
                <MessageCircle className="mr-2 h-4 w-4" />
                Bắt đầu trò chuyện
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="lg" variant="outline" className="border-background/20 bg-transparent text-background hover:bg-background/10 hover:text-background">
                Xem Dashboard minh họa
              </Button>
            </Link>
          </div>
          <p className="mt-3 text-xs text-background/60">Chỉ giáo dục &amp; thông tin — không phải lời khuyên đầu tư.</p>
        </div>
      </section>
    </div>
  )
}
