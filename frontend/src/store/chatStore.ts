"use client"
import { create } from "zustand"
import {
  CHART_LIBRARY_ROUTE,
  type ChartSpec,
  type ChartType,
} from "@/lib/chart-spec"

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt: number
  latencyMs?: number
  requestId?: string
}

export type DashboardChart = {
  id: string
  spec: ChartSpec
  originMessageId: string
  createdAt: number
}

type ChatStore = {
  messages: ChatMessage[]
  isStreaming: boolean
  input: string
  chartSpecs: DashboardChart[]
  activeChartId: string | null
  addMessage: (m: ChatMessage) => void
  setMessages: (msgs: ChatMessage[]) => void
  setIsStreaming: (v: boolean) => void
  setInput: (v: string) => void
  appendToLastAssistant: (chunk: string) => void
  clear: () => void
  setChartSpec: (spec: ChartSpec, originMessageId: string) => void
  overrideChartType: (id: string, chart_type: ChartType) => void
  setActiveChart: (id: string | null) => void
  clearCharts: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isStreaming: false,
  input: "",
  chartSpecs: [],
  activeChartId: null,
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
  setChartSpec: (spec, originMessageId) =>
    set((s) => {
      const entry: DashboardChart = {
        id: crypto.randomUUID(),
        spec,
        originMessageId,
        createdAt: Date.now(),
      }
      return { chartSpecs: [...s.chartSpecs, entry].slice(-20), activeChartId: entry.id }
    }),
  overrideChartType: (id, chart_type) =>
    set((s) => {
      const base = s.chartSpecs.find((c) => c.id === id)
      if (!base) return {}
      const entry: DashboardChart = {
        id: crypto.randomUUID(),
        spec: {
          ...base.spec,
          chart_type,
          library: CHART_LIBRARY_ROUTE[chart_type],
          series: base.spec.series.map((se) => ({ ...se, type: chart_type })),
        },
        originMessageId: base.originMessageId,
        createdAt: Date.now(),
      }
      return { chartSpecs: [...s.chartSpecs, entry].slice(-20), activeChartId: entry.id }
    }),
  setActiveChart: (id) => set({ activeChartId: id }),
  clearCharts: () => set({ chartSpecs: [], activeChartId: null }),
}))
