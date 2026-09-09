"use client"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { ChartSpec } from "@/lib/chart-spec"

type Row = Record<string, string | number | null | undefined>

const PALETTE = ["#2563eb", "#f59e0b", "#10b981", "#8b5cf6", "#ef4444", "#06b6d4", "#f97316"]

/** Recharts cho line/bar/area/pie/donut/scatter. Single-series chính xác, multi-series best-effort. */
export function RechartsGeneric({ spec }: { spec: ChartSpec }) {
  const rows = spec.data as Row[]
  const { x_field, y_field, series } = spec
  if (rows.length === 0) return <p className="text-sm text-muted-foreground">Không có dữ liệu.</p>

  if (spec.chart_type === "pie" || spec.chart_type === "donut") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip />
          <Legend />
          <Pie
            data={rows}
            dataKey={String(y_field)}
            nameKey={String(x_field)}
            innerRadius={spec.chart_type === "donut" ? "45%" : 0}
            outerRadius="80%"
            labelLine={false}
          >
            {rows.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (spec.chart_type === "scatter") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey={String(x_field)} tick={{ fontSize: 11 }} />
          <YAxis dataKey={String(y_field)} tick={{ fontSize: 11 }} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <Legend />
          <Scatter data={rows} fill={PALETTE[0]} name={series[0]?.name ?? String(y_field)} />
        </ScatterChart>
      </ResponsiveContainer>
    )
  }

  if (spec.chart_type === "bar") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey={String(x_field)} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          {series.map((s, i) => (
            <Bar key={s.name} dataKey={String(y_field)} name={s.name} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (spec.chart_type === "area") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey={String(x_field)} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          {series.map((s, i) => (
            <Area
              key={s.name}
              type="monotone"
              dataKey={String(y_field)}
              name={s.name}
              stroke={PALETTE[i % PALETTE.length]}
              fill={PALETTE[i % PALETTE.length]}
              fillOpacity={0.25}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  // default: line
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey={String(x_field)} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        {series.map((s, i) => (
          <Line
            key={s.name}
            type="monotone"
            dataKey={String(y_field)}
            name={s.name}
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
