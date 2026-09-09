import { getServerSession } from "next-auth"
import { authOptions } from "@/auth"
import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"
export async function GET(req: Request) {
  const session = await getServerSession(authOptions)
  const role = (session?.user as unknown as { role?: string })?.role
  if (!session || role !== "admin") {
    return Response.json({ detail: "Admin required" }, { status: 403 })
  }
  const token = (session as unknown as { accessToken?: string })?.accessToken || (session?.user as unknown as { accessToken?: string })?.accessToken
  const url = new URL(req.url)
  const qs = url.search
  try {
    const res = await fetch(`${getBackendUrl()}/api/v1/traces${qs}`, {
      cache: "no-store",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const data = await res.json()
    return Response.json(data, { headers: { "Cache-Control": "no-cache" }, status: res.status })
  } catch (e) {
    return Response.json({ enabled: false, count: 0, traces: [], error: String(e) }, { status: 503 })
  }
}
