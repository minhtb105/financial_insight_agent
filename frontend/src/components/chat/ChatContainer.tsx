"use client"
/* eslint-disable react-hooks/exhaustive-deps -- intentional mount-only effects for localStorage */
import { useEffect, useRef } from "react"
import { useSession } from "next-auth/react"
import { useChatStore } from "@/store/chatStore"
import { useChatStream } from "@/hooks/useChatStream"
import { MessageBubble } from "./MessageBubble"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card } from "@/components/ui/card"
import { Send, Square, Trash2, Sparkles } from "lucide-react"

const SUGGESTIONS = [
  "Giá đóng cửa của VCB hôm qua là bao nhiêu?",
  "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
  "So sánh khối lượng giao dịch VIC với HPG trong 1 tuần.",
  "Trong các mã FPT, MWG, VNM mã nào có giá cao nhất?",
  "PE của VNM hiện tại là bao nhiêu?",
  "Có tin tức gì về VCB trong tuần này không?",
]

export function ChatContainer() {
  const { messages, isStreaming, input, setInput, clear } = useChatStore()
  const { send, stop } = useChatStream()
  const { data: session } = useSession()
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  // Per-user localStorage key to avoid demo vs admin contamination
  const storageKey = `finsight-chat:${(session?.user as { email?: string })?.email ?? "default"}`

  useEffect(() => {
    const key = storageKey
    const saved = localStorage.getItem(key)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0 && messages.length === 0) {
          useChatStore.setState({ messages: parsed.slice(-50) })
        }
      } catch {}
    }
  }, [storageKey])
  useEffect(() => {
    if (messages.length > 0) localStorage.setItem(storageKey, JSON.stringify(messages.slice(-100)))
  }, [messages.length, storageKey])

  const handleSend = async () => {
    const q = input.trim()
    if (!q || isStreaming) return
    setInput("")
    await send(q)
  }

  const handleClear = async () => {
    clear()
    localStorage.removeItem(storageKey)
    try {
      const res = await fetch("/api/memory", { method: "DELETE" })
      if (!res.ok) {
        console.warn("Failed to clear server memory:", res.status, await res.text().catch(() => ""))
      }
    } catch (err) {
      console.warn("Failed to clear server memory:", err)
    }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem-3rem)] md:h-[calc(100vh-3.5rem)] flex-col">
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-background to-muted/20">
        {messages.length === 0 ? (
          <div className="mx-auto max-w-3xl py-8">
            <div className="text-center mb-8">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-2xl font-bold tracking-tight">Chào mừng đến Financial Insight Agent</h2>
              <p className="mt-2 text-muted-foreground">Trợ lý AI phân tích chứng khoán Việt Nam — giáo dục có trích dẫn, không phải lời khuyên đầu tư.</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <Card key={s} className="p-3 cursor-pointer hover:bg-accent transition-colors" onClick={() => setInput(s)}>
                  <p className="text-sm">{s}</p>
                </Card>
              ))}
            </div>
            <p className="mt-6 text-center text-xs text-muted-foreground">Mọi con số đều kèm citation [TICKER: ...] để bạn kiểm chứng. Chỉ phục vụ giáo dục & thông tin.</p>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((m, idx) => (
              <MessageBubble key={m.id} role={m.role} content={m.content} isStreaming={isStreaming && idx === messages.length - 1 && m.role === "assistant"} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="border-t bg-background p-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="Nhập câu hỏi, ví dụ: Giá VCB hôm nay? (Enter để gửi, Shift+Enter xuống dòng)"
              className="min-h-[48px] max-h-[120px] resize-none"
              rows={2}
              disabled={isStreaming}
            />
            <div className="flex flex-col gap-2">
              {isStreaming ? (
                <Button variant="destructive" size="icon" onClick={stop} aria-label="Dừng">
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={handleSend} disabled={!input.trim()} size="icon" aria-label="Gửi">
                  <Send className="h-4 w-4" />
                </Button>
              )}
              <Button variant="ghost" size="icon" onClick={handleClear} title="Xóa lịch sử">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Nhấn Enter để gửi • Tối đa 1000 ký tự • Dữ liệu từ vnstock</p>
        </div>
      </div>
    </div>
  )
}
