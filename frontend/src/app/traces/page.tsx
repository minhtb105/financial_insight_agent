import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/auth"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"

async function fetchTraces() {
  const base = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/api/v1/traces?limit=20`, { cache: "no-store" })
    if (!res.ok) return { enabled: false, traces: [] }
    return await res.json()
  } catch { return { enabled: false, traces: [] } }
}

export default async function TracesPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect("/login")
  const data = await fetchTraces()

  return (
    <div className="container mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Traces</h1>
        <p className="text-muted-foreground">Lịch sử xử lý agent — quan sát & debug</p>
      </div>
      {!data.enabled ? (
        <Card><CardContent className="p-6 text-sm text-muted-foreground">Tracing chưa bật hoặc backend chưa sẵn sàng. Bật <code>TRACING_ENABLED</code> trong backend để xem traces.</CardContent></Card>
      ) : (
        <div className="grid gap-3">
          {(data.traces ?? []).length === 0 ? (
            <Card><CardContent className="p-6 text-sm text-muted-foreground">Chưa có trace nào.</CardContent></Card>
          ) : (
            (data.traces as Array<{ trace_id: string; root_name?: string; status: string; duration_ms?: number; num_spans: number }>).map((t) => (
              <Link key={t.trace_id} href={`/traces/${t.trace_id}`}>
                <Card className="hover:bg-accent/50 transition-colors">
                  <CardHeader className="py-3">
                    <CardTitle className="text-sm font-mono">{t.trace_id.slice(0, 12)}…</CardTitle>
                    <CardDescription className="flex items-center gap-2">
                      <Badge variant={t.status === "ok" ? "default" : t.status === "error" ? "destructive" : "secondary"}>{t.status}</Badge>
                      {t.root_name && <span>{t.root_name}</span>}
                      {t.duration_ms && <span>{t.duration_ms.toFixed(0)} ms</span>}
                      <span>{t.num_spans} spans</span>
                    </CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            ))
          )}
        </div>
      )}
    </div>
  )
}
