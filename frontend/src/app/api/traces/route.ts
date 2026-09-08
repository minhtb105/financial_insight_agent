export const dynamic = "force-dynamic"
const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
export async function GET(req: Request) {
  const url = new URL(req.url)
  const qs = url.search
  try {
    const res = await fetch(`${BACKEND_URL.replace(/\/$/, "")}/api/v1/traces${qs}`, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { headers: { "Cache-Control": "no-cache" } })
  } catch (e) {
    return Response.json({ enabled: false, count: 0, traces: [], error: String(e) }, { status: 503 })
  }
}
