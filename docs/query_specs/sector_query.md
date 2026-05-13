# sector_query

## Overview
Sector query analyzes and ranks stocks within a specified industry sector by performance or volume. Priority: low. Selected when the query contains keywords like "ngành", "sector", "nhóm ngành", "cùng ngành".

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| sector | Yes | string | "" | Sector name to analyze (e.g., "ngân hàng", "công nghệ") |
| metric | No | string | "performance" | Sort metric: "performance" or "volume" |
| timeframe | No | string | "1w" | Analysis timeframe (informational in current implementation) |

## Input Constraints
- `sector` must be non-empty; otherwise returns `"Missing sector parameter"` error
- Sector matching is **case-insensitive** using `str.lower().contains(sector.lower())` on the company overview's `sector` or `industry` column
- Column name fallback: tries `sector` → `industry` → `sector` (with `company_code` ticker column)
- If no tickers match the sector, returns `"Sector data unavailable"` with empty `suggested_tickers`
- Results are cached per `(sector, metric, timeframe)` with TTL of 2 hours
- Tickers with insufficient price data (fewer than 2 data points) are silently excluded

## Output Contract

### Success Response
```json
{
  "sector": "string",
  "metric": "string",
  "timeframe": "string",
  "ranked_tickers": [
    {
      "rank": "int",
      "ticker": "string",
      "performance_pct": "float",
      "avg_volume": "int"
    }
  ],
  "total_tickers": "int"
}
```

### Error Response
```json
{ "error": "Missing sector parameter" }
```
```json
{ "sector": "string", "error": "Sector data unavailable", "suggested_tickers": [] }
```

## Field Definitions

### Metric Enum
| Value | Description |
|-------|-------------|
| performance | Rank by performance_pct descending |
| volume | Rank by avg_volume descending |

## Examples

### Example 1: Sector performance ranking
Input: "Hiệu suất các cổ phiếu ngành ngân hàng"
Parsed: `{"query_type": "sector_query", "sector": "ngân hàng", "metric": "performance"}`
Response: `{"sector": "ngân hàng", "metric": "performance", "timeframe": "1w", "ranked_tickers": [{"rank": 1, "ticker": "VCB", "performance_pct": 2.5, "avg_volume": 1500000}, {"rank": 2, "ticker": "BID", "performance_pct": 1.8, "avg_volume": 2000000}, {"rank": 3, "ticker": "CTG", "performance_pct": 0.5, "avg_volume": 1800000}], "total_tickers": 3}`

### Example 2: Sector volume ranking
Input: "Cổ phiếu ngành thép có volume cao nhất"
Parsed: `{"query_type": "sector_query", "sector": "thép", "metric": "volume"}`
Response: `{"sector": "thép", "metric": "volume", "timeframe": "1w", "ranked_tickers": [{"rank": 1, "ticker": "HPG", "performance_pct": -0.3, "avg_volume": 5000000}, {"rank": 2, "ticker": "NKG", "performance_pct": 1.2, "avg_volume": 800000}], "total_tickers": 2}`

### Example 3: Sector not found
Input: "Phân tích ngành năng lượng mặt trời"
Parsed: `{"query_type": "sector_query", "sector": "năng lượng mặt trời", "metric": "performance"}`
Response: `{"sector": "năng lượng mặt trời", "error": "Sector data unavailable", "suggested_tickers": []}`

### Example 4: Missing sector parameter
Input: "Phân tích theo ngành"
Parsed: `{"query_type": "sector_query"}`
Response: `{"error": "Missing sector parameter"}`

## Service Mapping
- Handler: `application.services.market.sector_service.handle_sector_query`
- Tool: `handle_sector_query_tool` (in `application.agents.tool_registry`)