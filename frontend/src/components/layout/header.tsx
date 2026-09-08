"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { LayoutDashboard, MessageCircle, Activity, LogOut, TrendingUp } from "lucide-react"
import { useEffect, useState } from "react"

const NAV = [
  { href: "/chat", label: "Trò chuyện", icon: MessageCircle },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/traces", label: "Traces", icon: Activity },
]

export function Header() {
  const pathname = usePathname()
  const { data: session, status } = useSession()
  const [health, setHealth] = useState<"ok" | "down" | "loading">("loading")

  useEffect(() => {
    fetch("/api/health").then((r) => r.json()).then((j) => setHealth(j.status === "ok" || j.agent_ready !== false ? "ok" : "down")).catch(() => setHealth("down"))
  }, [])

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-6">
          <Link href={session ? "/chat" : "/"} className="flex items-center gap-2 font-semibold">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <TrendingUp className="h-4 w-4" />
            </div>
            <span className="hidden sm:inline">Financial Insight</span>
          </Link>
          {status === "authenticated" && (
            <nav className="hidden md:flex items-center gap-1">
              {NAV.map((item) => {
                const active = pathname?.startsWith(item.href)
                return (
                  <Link key={item.href} href={item.href} className={cn("inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors", active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground")}>
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={health === "ok" ? "default" : health === "down" ? "destructive" : "secondary"} className="hidden sm:inline-flex">
            <span className={cn("mr-1.5 h-2 w-2 rounded-full", health === "ok" ? "bg-green-500" : health === "down" ? "bg-red-500" : "bg-yellow-500")} />
            {health === "ok" ? "Agent sẵn sàng" : health === "down" ? "Agent lỗi" : "Đang kiểm tra"}
          </Badge>
          {status === "authenticated" ? (
            <>
              <span className="hidden sm:inline text-sm text-muted-foreground">{session.user?.name ?? session.user?.email}</span>
              <Button variant="ghost" size="sm" onClick={() => signOut({ callbackUrl: "/login" })}>
                <LogOut className="h-4 w-4" /> Đăng xuất
              </Button>
            </>
          ) : status === "unauthenticated" ? (
            <Link href="/login"><Button size="sm">Đăng nhập</Button></Link>
          ) : null}
        </div>
      </div>
      {status === "authenticated" && (
        <div className="md:hidden border-t bg-background">
          <nav className="flex items-center justify-around px-2 py-1">
            {NAV.map((item) => {
              const active = pathname?.startsWith(item.href)
              return (
                <Link key={item.href} href={item.href} className={cn("flex flex-col items-center gap-1 rounded-md px-3 py-1.5 text-xs", active ? "text-primary bg-accent" : "text-muted-foreground")}>
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>
      )}
    </header>
  )
}
