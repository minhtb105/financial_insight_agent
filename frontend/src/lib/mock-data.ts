export type PriceRow = {
  ticker: string
  price: number
  change: number
  changePct: number
  volume: number
  sma9?: number
  rsi14?: number
}

export const MOCK_PRICES: PriceRow[] = [
  { ticker: "VCB", price: 92500, change: 1200, changePct: 1.31, volume: 3_250_000, sma9: 91200, rsi14: 62 },
  { ticker: "FPT", price: 132000, change: -800, changePct: -0.6, volume: 2_100_000, sma9: 130500, rsi14: 48 },
  { ticker: "VNM", price: 68500, change: 350, changePct: 0.51, volume: 1_850_000, sma9: 67800, rsi14: 55 },
  { ticker: "HPG", price: 28500, change: 600, changePct: 2.15, volume: 18_500_000, sma9: 27800, rsi14: 68 },
  { ticker: "VIC", price: 42500, change: -200, changePct: -0.47, volume: 2_900_000, sma9: 42300, rsi14: 42 },
  { ticker: "MWG", price: 65500, change: 900, changePct: 1.39, volume: 4_100_000, sma9: 64200, rsi14: 60 },
]

export type Candle = { date: string; price: number; sma9: number; rsi: number }

export const MOCK_CANDLES: Candle[] = Array.from({ length: 30 }, (_, i) => {
  const base = 90000 + Math.sin(i / 3) * 3000 + i * 80
  return {
    date: `2026-08-${String(i + 1).padStart(2, "0")}`,
    price: Math.round(base),
    sma9: Math.round(base - 400 + Math.random() * 800),
    rsi: Math.round(40 + Math.random() * 30),
  }
})

export type PortfolioItem = {
  ticker: string
  qty: number
  avgPrice: number
  currentPrice: number
}

export const MOCK_PORTFOLIO: PortfolioItem[] = [
  { ticker: "FPT", qty: 100, avgPrice: 125000, currentPrice: 132000 },
  { ticker: "VCB", qty: 200, avgPrice: 88000, currentPrice: 92500 },
  { ticker: "HPG", qty: 500, avgPrice: 26500, currentPrice: 28500 },
]

export type SectorRow = {
  sector: string
  changePct: number
  volume: string
  topTicker: string
}

export const MOCK_SECTORS: SectorRow[] = [
  { sector: "Ngân hàng", changePct: 1.2, volume: "320M", topTicker: "VCB" },
  { sector: "Bất động sản", changePct: -0.8, volume: "210M", topTicker: "VIC" },
  { sector: "Công nghệ", changePct: 2.1, volume: "85M", topTicker: "FPT" },
  { sector: "Thép", changePct: 1.8, volume: "150M", topTicker: "HPG" },
  { sector: "Tiêu dùng", changePct: 0.4, volume: "95M", topTicker: "VNM" },
]
