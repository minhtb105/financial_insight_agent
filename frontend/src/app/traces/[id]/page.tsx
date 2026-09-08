import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/auth"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getBackendUrl } from "@/lib/backend"

async function fetchTrace(id: string) {
  try {
    const res = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(id)}`, { cache: "no-store" })
    const data = await res.json()
    return { ok: res.ok, data }
  } catch (e) { return { ok: false, data: { detail: String(e) } } }
}

export default async function TraceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const session = await getServerSession(authOptions)
  if (!session) redirect("/login")
  const { id } = await params
  const { ok, data } = await fetchTrace(id)

  return (
    <div className="container mx-auto p-4 md:p-6 space-y-6">
      <h1 className="text-xl font-bold font-mono break-all">Trace {id}</h1>
      {!ok ? (
        <Card><CardContent className="p-6 text-sm text-destructive">{data.detail ?? "Không tìm thấy trace"}</CardContent></Card>
      ) : (
        <Card>
          <CardHeader><CardTitle>Chi tiết spans</CardTitle></CardHeader>
          <CardContent>
            <pre className="overflow-auto rounded bg-muted p-4 text-xs">{JSON.stringify(data.trace ?? data, null, 2)}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
