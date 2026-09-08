"use client"
import { useCallback, useRef } from "react"
import { parseSSEChunk, type SSEEvent } from "@/lib/sse"
import { useChatStore } from "@/store/chatStore"

export function useChatStream() {
  const { addMessage, appendToLastAssistant, setIsStreaming } = useChatStore()
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(
    async (query: string) => {
      if (!query.trim()) return
      const userId = crypto.randomUUID()
      addMessage({ id: userId, role: "user", content: query, createdAt: Date.now() })
      const assistantId = crypto.randomUUID()
      addMessage({ id: assistantId, role: "assistant", content: "", createdAt: Date.now() })
      setIsStreaming(true)

      const controller = new AbortController()
      abortRef.current = controller

      try {
        const res = await fetch("/api/ask-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
          signal: controller.signal,
        })

        if (!res.ok || !res.body) {
          const txt = await res.text()
          appendToLastAssistant(`Lỗi: ${res.status} ${txt.slice(0, 500)}`)
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const { events, rest } = parseSSEChunk(buffer)
          buffer = rest
          for (const ev of events) handleEvent(ev)
        }
        // flush remaining
        if (buffer.trim()) {
          const { events } = parseSSEChunk(buffer + "\n\n")
          for (const ev of events) handleEvent(ev)
        }

        function handleEvent(ev: SSEEvent) {
          if (ev.event === "chunk") {
            // chunk data may be plain string or JSON escaped?
            let chunk = ev.data
            try {
              // if data is JSON stringified
              const parsed = JSON.parse(ev.data)
              if (typeof parsed === "string") chunk = parsed
            } catch {}
            appendToLastAssistant(chunk)
          } else if (ev.event === "final") {
            try {
              const final = JSON.parse(ev.data)
              if (final.latency_ms) {
                // optional: could update message with latency
              }
            } catch {}
          } else if (ev.event === "error") {
            appendToLastAssistant(`\n\n⚠️ Lỗi: ${ev.data}`)
          }
        }
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") {
          appendToLastAssistant(" (đã dừng)")
        } else {
          appendToLastAssistant(`\n\n⚠️ Lỗi kết nối: ${String(e).slice(0, 300)}`)
        }
      } finally {
        setIsStreaming(false)
        abortRef.current = null
      }
    },
    [addMessage, appendToLastAssistant, setIsStreaming]
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [setIsStreaming])

  return { send, stop }
}
