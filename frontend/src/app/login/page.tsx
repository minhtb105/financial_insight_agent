"use client"
import { useState } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { z } from "zod"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

const loginSchema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(3, "Mật khẩu tối thiểu 3 ký tự"),
})

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("demo@finsight.vn")
  const [password, setPassword] = useState("demo123")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const parsed = loginSchema.safeParse({ email, password })
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Dữ liệu không hợp lệ")
      return
    }
    setLoading(true)
    setError("")
    const res = await signIn("credentials", { email, password, redirect: false })
    setLoading(false)
    if (res?.error) {
      setError("Email hoặc mật khẩu không đúng. Kiểm tra lại hoặc đăng ký tài khoản mới.")
    } else if (res?.ok) {
      router.push("/chat")
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center p-4 bg-muted/30">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl">Đăng nhập</CardTitle>
          <CardDescription>Đăng nhập để trò chuyện. Mỗi tài khoản có bộ nhớ & lịch sử riêng.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="demo@finsight.vn" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mật khẩu</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••" />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>{loading ? "Đang đăng nhập..." : "Đăng nhập"}</Button>
          </form>
          <div className="mt-4 text-center text-sm">
            Chưa có tài khoản? <Link href="/signup" className="text-primary hover:underline">Đăng ký</Link>
          </div>
          <div className="mt-4 rounded-lg bg-muted p-3 text-xs">
            <p className="font-medium mb-1">Tài khoản mặc định:</p>
            <p>• demo@finsight.vn / demo123 (user)</p>
            <p>• admin@finsight.vn / admin123 (admin — xem được Traces)</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
