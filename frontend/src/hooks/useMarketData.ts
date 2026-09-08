"use client"
import { useEffect, useState } from "react"

type FetchState<T> = { data: T | null; loading: boolean; error: string | null }

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function usePrices(tickers: string[], field = "close", days = 30) {
  const [state, setState] = useState<FetchState<Record<string, unknown>>>({ data: null, loading: true, error: null })
  const key = tickers.join(",")
  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset loading on key change
    setState({ data: null, loading: true, error: null })
    fetchJson(`/api/market/prices?tickers=${encodeURIComponent(key)}&field=${field}&days=${days}`)
      .then((d) => {
        if (!cancelled) setState({ data: d as Record<string, unknown>, loading: false, error: null })
      })
      .catch((e: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: e.message })
      })
    return () => {
      cancelled = true
    }
  }, [key, field, days])
  return state
}

export type Candle = { date: string; price: number; sma9?: number; rsi?: number; open?: number; high?: number; low?: number; volume?: number }

export function useCandles(ticker: string, days = 30) {
  const [state, setState] = useState<FetchState<{ ticker: string; candles: Candle[]; count: number }>>({ data: null, loading: true, error: null })
  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset loading on ticker change
    setState({ data: null, loading: true, error: null })
    fetchJson<{ ticker: string; candles: Candle[]; count: number }>(`/api/market/candles?ticker=${encodeURIComponent(ticker)}&days=${days}`)
      .then((d) => {
        if (!cancelled) setState({ data: d, loading: false, error: null })
      })
      .catch((e: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: e.message })
      })
    return () => {
      cancelled = true
    }
  }, [ticker, days])
  return state
}

export function usePortfolio() {
  const [state, setState] = useState<FetchState<Record<string, unknown>>>({ data: null, loading: true, error: null })
  useEffect(() => {
    let cancelled = false
    fetchJson<Record<string, unknown>>(`/api/market/portfolio?field=portfolio_summary`)
      .then((d) => {
        if (!cancelled) setState({ data: d, loading: false, error: null })
      })
      .catch((e: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: e.message })
      })
    return () => {
      cancelled = true
    }
  }, [])
  return state
}

export type SectorRow = { sector: string; changePct: number; topTicker: string; totalTickers?: number }

export function useSectors(timeframe: string = "1w") {
  const [state, setState] = useState<FetchState<{ sectors: SectorRow[] }>>({ data: null, loading: true, error: null })
  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset loading on timeframe change
    setState({ data: null, loading: true, error: null })
    fetchJson<{ sectors: SectorRow[] }>(`/api/market/sectors?timeframe=${timeframe}`)
      .then((d) => {
        if (!cancelled) setState({ data: d, loading: false, error: null })
      })
      .catch((e: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: e.message })
      })
    return () => {
      cancelled = true
    }
  }, [timeframe])
  return state
}
