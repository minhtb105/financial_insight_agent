import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function GET() {
  const target = `${getBackendUrl()}/api/v1/market/portfolio?field=portfolio_summary`
  try {
    const res = await fetch(target, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { headers: { "Cache-Control": "no-cache" } })
  } catch (e) {
    return Response.json({ error: String(e), portfolio_value: 0 }, { status: 503 })
  }
}
