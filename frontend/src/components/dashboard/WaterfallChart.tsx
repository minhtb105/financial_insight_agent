"use client"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { ChartSpec } from "@/lib/chart-spec"

function toNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

/** Waterfall ghép từ stacked Bar: base trong suốt + delta tô màu theo dấu. */
export function WaterfallChart({ spec }: { spec: ChartSpec }) {
  const rows = spec.data as Array<Record<string, unknown>>
  type Step = { label: string; base: number; delta: number; up: boolean; total: number }
  const steps = rows.reduce<Step[]>((acc, r, i) => {
    const prev = acc.length > 0 ? acc[acc.length - 1].total : 0
    const label = String(r[spec.x_field] ?? `#${i + 1}`)
    const raw = toNum(r[spec.y_field])
    const base = raw >= 0 ? prev : prev + raw
    return [...acc, { label, base, delta: Math.abs(raw), up: raw >= 0, total: prev + raw }]
  }, [])

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={steps}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v, name) => [v, name === "delta" ? "Biến động" : name]} />
        <Legend />
        <Bar dataKey="base" stackId="wf" fill="transparent" isAnimationActive={false} name="Nền" />
        <Bar dataKey="delta" stackId="wf" name="Biến động">
          {steps.map((s, i) => (
            <Cell key={i} fill={s.up ? "#16a34a" : "#dc2626"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
