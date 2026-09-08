export const dynamic = "force-dynamic"
const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL.replace(/\/$/, "")}/health`, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { headers: { "Cache-Control": "no-cache" } })
  } catch (e) {
    return Response.json({ status: "down", agent_ready: false, error: String(e) }, { status: 503 })
  }
}
