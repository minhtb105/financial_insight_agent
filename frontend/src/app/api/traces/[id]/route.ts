import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  try {
    const res = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(id)}`, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch (e) {
    return Response.json({ detail: String(e) }, { status: 503 })
  }
}
