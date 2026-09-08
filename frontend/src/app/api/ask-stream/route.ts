import { NextRequest } from "next/server"
import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const query = body.query as string | undefined
  if (!query || !query.trim()) {
    return new Response(JSON.stringify({ detail: "Query rỗng" }), { status: 400, headers: { "Content-Type": "application/json" } })
  }

  const target = `${getBackendUrl()}/api/v1/ask-stream`

  // Forward to FastAPI and proxy SSE
  const upstream = await fetch(target, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
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
