"use client"
import { create } from "zustand"

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt: number
  latencyMs?: number
  requestId?: string
}

type ChatStore = {
  messages: ChatMessage[]
  isStreaming: boolean
  input: string
  addMessage: (m: ChatMessage) => void
  setMessages: (msgs: ChatMessage[]) => void
  setIsStreaming: (v: boolean) => void
  setInput: (v: string) => void
  appendToLastAssistant: (chunk: string) => void
  clear: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isStreaming: false,
  input: "",
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  setMessages: (msgs) => set({ messages: msgs }),
  setIsStreaming: (v) => set({ isStreaming: v }),
  setInput: (v) => set({ input: v }),
  appendToLastAssistant: (chunk) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + chunk }
      }
      return { messages: msgs }
    }),
  clear: () => set({ messages: [] }),
}))
