# financial_ratio_query

## Overview
Fetches financial ratios (P/E, P/B, ROE, EPS, etc.) for given tickers with interpretation and supporting metrics. Priority: normal. Selected when user asks for valuation ratios, profitability metrics, liquidity ratios, or financial health indicators.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | List of stock ticker symbols |
| requested_field | No | string | "pe" | Target ratio type |
| period | No | string | — | Reporting period: `quarter` or `year` |
| quarter | No | int | — | Quarter number (1-4), requires `period: "quarter"` |
| year | No | int | — | Fiscal year |
| compare_with | No | string[] | — | Tickers to compare against (uses `compare_financial_ratios`) |

## Input Constraints
- At least one ticker is required
- `requested_field` must be one of the predefined ratio types; unsupported values are silently ignored
- When `compare_with` is provided, the handler calls `compare_financial_ratios` which returns a comparison summary with sorted values
- If no financial data exists for a ticker, `{"error": "No financial data available"}` is returned for that ticker

## Output Contract

### Success Response — Single Ratio
```json
{
  "TICKER": {
    "pe_ratio": {
      "value": 15.2,
      "eps": 5000,
      "current_price": 76000,
      "interpretation": "Moderate P/E - Reasonable valuation",
      "time_range": "Latest"
    }
  }
}
```

### Success Response — Comparison
```json
{
  "FPT": { "pe_ratio": { "value": 18.5, ... } },
  "VNM": { "pe_ratio": { "value": 15.2, ... } },
  "comparison": {
    "sorted_by_value": [["FPT", 18.5], ["VNM", 15.2]],
    "highest": ["FPT", 18.5],
    "lowest": ["VNM", 15.2],
    "mean": 16.85,
    "count": 2
  }
}
```

### Error Response
```json
{ "error": "Missing ticker" }
```

```json
{ "error": "No financial data available" }
```

```json
{ "error": "No ratios calculated" }
```

## Field Definitions

### Requested Field Enum
| Value | Ratio Key | Supporting Fields |
|-------|-----------|-------------------|
| `pe` | `pe_ratio` | `eps`, `current_price`, `interpretation`, `time_range` |
| `pb` | `pb_ratio` | `book_value_per_share`, `current_price`, `interpretation`, `time_range` |
| `roe` | `roe` | `net_profit`, `total_equity`, `interpretation`, `time_range` |
| `eps` | `eps` | `net_profit`, `shares_outstanding`, `interpretation`, `time_range` |
| `debt_to_equity` | `debt_to_equity` | `total_liabilities`, `total_equity`, `interpretation`, `time_range` |
| `current_ratio` | `current_ratio` | `current_assets`, `current_liabilities`, `interpretation`, `time_range` |
| `profit_margin` | `profit_margin` | `net_profit`, `revenue`, `interpretation`, `time_range` |
| `quick_ratio` | `quick_ratio` | `quick_assets`, `current_liabilities`, `interpretation`, `time_range` |
| `asset_turnover` | `asset_turnover` | `revenue`, `total_assets`, `interpretation`, `time_range` |
| `dividend_yield` | `dividend_yield` | `dividend_per_share`, `current_price`, `interpretation`, `time_range` |

## Examples

### Example 1: Basic P/E query
Input: "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?"
Parsed: `{"query_type": "financial_ratio_query", "requested_field": "pe", "tickers": ["VNM"]}`
Response: `{"VNM": {"pe_ratio": {"value": 15.2, "eps": 5000, "current_price": 76000, "interpretation": "Moderate P/E - Reasonable valuation", "time_range": "Latest"}}}`

### Example 2: ROE comparison
Input: "So sánh ROE giữa FPT và VNM trong 3 năm gần đây"
Parsed: `{"query_type": "financial_ratio_query", "requested_field": "roe", "tickers": ["FPT"], "compare_with": ["VNM"], "years": 3}`
Response: `{"FPT": {"roe": {...}}, "VNM": {"roe": {...}}, "comparison": {"sorted_by_value": [...], "highest": [...], "lowest": [...], "mean": ..., "count": 2}}`

### Example 3: EPS with quarter
Input: "EPS của HPG trong quý 3/2024 là bao nhiêu?"
Parsed: `{"query_type": "financial_ratio_query", "requested_field": "eps", "tickers": ["HPG"], "period": "quarter", "quarter": 3, "year": 2024}`
Response: `{"HPG": {"eps": {"value": 3500, "net_profit": ..., "shares_outstanding": ..., "interpretation": "Moderate EPS - Good profitability", "time_range": "Latest"}}}`

## Service Mapping
- Handler: `src.application.services.financial.financial_ratio_service.handle_financial_ratio_query`
- Tool: `handle_financial_ratio_tool`