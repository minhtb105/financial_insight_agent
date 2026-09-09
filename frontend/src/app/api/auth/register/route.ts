import { NextRequest, NextResponse } from "next/server"
import { getBackendUrl } from "@/lib/backend"

export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const { email, password, name } = body as { email?: string; password?: string; name?: string }
  if (!email || !password) {
    return NextResponse.json({ detail: "Thiếu email hoặc mật khẩu" }, { status: 400 })
  }
  try {
    const res = await fetch(`${getBackendUrl()}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name: name || "" }),
    })
    const data = await res.json().catch(() => ({}))
    return NextResponse.json(data, { status: res.status })
  } catch (e) {
    return NextResponse.json({ detail: `Backend unreachable: ${String(e)}` }, { status: 502 })
  }
}
