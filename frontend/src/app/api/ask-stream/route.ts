import { NextRequest } from "next/server"
import { getServerSession } from "next-auth"
import { authOptions } from "@/auth"
import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const query = body.query as string | undefined
  if (!query || !query.trim()) {
    return new Response(JSON.stringify({ detail: "Query rỗng" }), { status: 400, headers: { "Content-Type": "application/json" } })
  }

  const session = await getServerSession(authOptions)
  const token = (session as unknown as { accessToken?: string })?.accessToken || (session?.user as unknown as { accessToken?: string })?.accessToken
  if (!token) {
    return new Response(JSON.stringify({ detail: "Chưa đăng nhập" }), { status: 401, headers: { "Content-Type": "application/json" } })
  }

  const target = `${getBackendUrl()}/api/v1/ask-stream`

  // Forward to FastAPI and proxy SSE (giữ activeChartSpec để follow-up về chart)
  const upstream = await fetch(target, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ query, activeChartSpec: body.activeChartSpec ?? null }),
  })

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => "")
    return new Response(text || "Upstream error", { status: upstream.status, headers: { "Content-Type": "text/plain" } })
  }

  // Stream through
  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  })
}
