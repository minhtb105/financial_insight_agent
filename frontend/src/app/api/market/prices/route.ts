import { NextRequest } from "next/server"
import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.search
  const target = `${getBackendUrl()}/api/v1/market/prices${qs}`
  try {
    const res = await fetch(target, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { headers: { "Cache-Control": "no-cache" } })
  } catch (e) {
    return Response.json({ error: String(e), tickers: [] }, { status: 503 })
  }
}
