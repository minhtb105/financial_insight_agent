export const dynamic = "force-dynamic"
const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  try {
    const res = await fetch(`${BACKEND_URL.replace(/\/$/, "")}/api/v1/traces/${encodeURIComponent(id)}`, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch (e) {
    return Response.json({ detail: String(e) }, { status: 503 })
  }
}
