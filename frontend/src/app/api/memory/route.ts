import { getServerSession } from "next-auth"
import { authOptions } from "@/auth"
import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"

export async function GET(request: Request) {
  const session = await getServerSession(authOptions)
  const token = (session as unknown as { accessToken?: string })?.accessToken || (session?.user as unknown as { accessToken?: string })?.accessToken
  if (!token) return Response.json({ detail: "Not authenticated" }, { status: 401 })
  const qs = new URL(request.url).searchParams.toString()
  const url = `${getBackendUrl()}/api/v1/memory${qs ? `?${qs}` : ""}`
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" })
  const data = await res.json().catch(() => ({}))
  return Response.json(data, { status: res.status })
}

export async function DELETE() {
  const session = await getServerSession(authOptions)
  const token = (session as unknown as { accessToken?: string })?.accessToken || (session?.user as unknown as { accessToken?: string })?.accessToken
  if (!token) return Response.json({ detail: "Not authenticated" }, { status: 401 })
  const res = await fetch(`${getBackendUrl()}/api/v1/memory`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } })
  const data = await res.json().catch(() => ({}))
  return Response.json(data, { status: res.status })
}
