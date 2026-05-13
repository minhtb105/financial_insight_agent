# indicator_query

## Overview
Computes technical indicators (SMA, RSI, MACD) for given tickers over a time range. Priority: normal. Selected when user asks for moving averages, RSI, MACD, or any technical indicator calculation.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | List of stock ticker symbols |
| requested_field | No | string | "sma" | Target indicator type: `sma`, `rsi`, or `macd` |
| indicator_params | No | dict | `{}` | Per-indicator parameters: `{sma: [20], rsi: [14], macd: [[12, 26]]}` |
| start | No | string (YYYY-MM-DD) | — | Explicit start date |
| end | No | string (YYYY-MM-DD) | — | Explicit end date |
| days | No | int | — | Lookback days |
| weeks | No | int | — | Lookback weeks |
| months | No | int | — | Lookback months |

## Input Constraints
- At least one ticker is required
- If `start` and `end` are not provided, one of `days`, `weeks`, or `months` must be set
- `indicator_params` keys must match the chosen `requested_field`; mismatched keys are silently ignored
- SMA/RSI periods default to `[20]` / `[14]` when not specified
- MACD default pair is `[(12, 26)]`

## Output Contract

### Success Response
```json
{
  "TICKER": {
    "sma_20": [{ "date": "2024-01-01", "sma": 105.5 }],
    "rsi_14": [{ "date": "2024-01-01", "rsi": 58.2 }],
    "macd_12_26": {
      "macd_line": [{ "date": "2024-01-01", "macd": 1.23 }],
      "signal_line": [{ "date": "2024-01-01", "signal": 1.15 }],
      "histogram": [{ "date": "2024-01-01", "histogram": 0.08 }]
    }
  }
}
```

### Error Response
```json
{ "error": "Missing ticker" }
```

```json
{ "error": "No data available" }
```

```json
{ "error": "No valid data found" }
```

## Field Definitions

### Requested Field Enum
| Value | Description |
|-------|-------------|
| `sma` | Simple Moving Average |
| `rsi` | Relative Strength Index |
| `macd` | Moving Average Convergence Divergence |

## Examples

### Example 1: Basic SMA query
Input: "Tính SMA9 cho VCB trong 1 tuần gần nhất."
Parsed: `{"query_type": "indicator_query", "requested_field": "sma", "tickers": ["VCB"], "indicator_params": {"sma": [9]}, "weeks": 1}`
Response: `{"VCB": {"sma_9": [{"date": "2024-01-05", "sma": 95.2}, {"date": "2024-01-04", "sma": 94.8}]}}`

### Example 2: RSI query without explicit params (defaults to period 14)
Input: "RSI14 của VIC từ đầu tháng 10 đến nay."
Parsed: `{"query_type": "indicator_query", "requested_field": "rsi", "tickers": ["VIC"], "indicator_params": {"rsi": [14]}}`
Response: `{"VIC": {"rsi_14": [{"date": "2024-10-31", "rsi": 62.1}, {"date": "2024-10-30", "rsi": 58.4}]}}`

### Example 3: MACD query
Input: "MACD của HPG 3 tháng gần nhất."
Parsed: `{"query_type": "indicator_query", "requested_field": "macd", "tickers": ["HPG"], "indicator_params": {"macd": [[12, 26]]}, "months": 3}`
Response: `{"HPG": {"macd_12_26": {"macd_line": [...], "signal_line": [...], "histogram": [...]}}}`

## Service Mapping
- Handler: `src.application.services.market.indicator_service.handle_indicator_query`
- Tool: `handle_indicator_tool`