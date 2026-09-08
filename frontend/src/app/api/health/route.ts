import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"
export async function GET() {
  try {
    const res = await fetch(`${getBackendUrl()}/health`, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { headers: { "Cache-Control": "no-cache" } })
  } catch (e) {
    return Response.json({ status: "down", agent_ready: false, error: String(e) }, { status: 503 })
  }
}
