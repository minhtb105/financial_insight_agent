# alert_query

## Overview
Alert query monitors price thresholds for given tickers and returns whether each has triggered. Priority: medium. Selected when the query contains keywords like "cảnh báo", "alert", "ngưỡng", "vượt", "chạm".

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | list[str] | — | Stock tickers to monitor |
| threshold | Yes | float | 0.0 | Price threshold value |
| condition | No | string | "above" | Comparison direction: "above" or "below" |
| timeframe | No | string | "1d" | Observation timeframe |

## Input Constraints
- `tickers` must be non-empty
- `threshold` must be non-zero (validated as `threshold == 0.0` → error)
- `condition` must be one of: `above`, `below`
- `timeframe` is informational only (service always fetches `interval="1d"`)
- If a ticker has no price data, it appears in results with an `error` field instead of price/triggered

## Output Contract

### Success Response
```json
{
  "alerts": [
    {
      "ticker": "string",
      "current_price": "float",
      "threshold": "float",
      "condition": "string",
      "triggered": "bool"
    }
  ],
  "timeframe": "string",
  "summary": {
    "total": "int",
    "triggered": "int"
  }
}
```

### Error Response
```json
{ "error": "Missing tickers or threshold parameter" }
```
```json
{ "error": "Alert monitoring requires price data" }
```

## Field Definitions

### Condition Enum
| Value | Description |
|-------|-------------|
| above | Triggered when current_price >= threshold |
| below | Triggered when current_price <= threshold |

## Examples

### Example 1: Basic alert check (above)
Input: "Cảnh báo khi giá FPT vượt 120000"
Parsed: `{"query_type": "alert_query", "tickers": ["FPT"], "threshold": 120000, "condition": "above"}`
Response: `{"alerts": [{"ticker": "FPT", "current_price": 125000, "threshold": 120000, "condition": "above", "triggered": true}], "timeframe": "1d", "summary": {"total": 1, "triggered": 1}}`

### Example 2: Alert below threshold
Input: "Cảnh báo nếu VNM xuống dưới 65000"
Parsed: `{"query_type": "alert_query", "tickers": ["VNM"], "threshold": 65000, "condition": "below"}`
Response: `{"alerts": [{"ticker": "VNM", "current_price": 70000, "threshold": 65000, "condition": "below", "triggered": false}], "timeframe": "1d", "summary": {"total": 1, "triggered": 0}}`

### Example 3: Multiple tickers
Input: "Kiểm tra alert cho FPT và VNM ở ngưỡng 100000"
Parsed: `{"query_type": "alert_query", "tickers": ["FPT", "VNM"], "threshold": 100000, "condition": "above"}`
Response: `{"alerts": [{"ticker": "FPT", "current_price": 125000, "threshold": 100000, "condition": "above", "triggered": true}, {"ticker": "VNM", "current_price": 70000, "threshold": 100000, "condition": "above", "triggered": false}], "timeframe": "1d", "summary": {"total": 2, "triggered": 1}}`

### Example 4: No price data (error per ticker)
Input: "Alert cho XYZ ở 50000"
Parsed: `{"query_type": "alert_query", "tickers": ["XYZ"], "threshold": 50000, "condition": "above"}`
Response: `{"alerts": [{"ticker": "XYZ", "error": "No price data available"}], "timeframe": "1d", "summary": {"total": 1, "triggered": 0}}`

### Example 5: Missing parameters
Input: "Cảnh báo giá"
Parsed: `{"query_type": "alert_query"}`
Response: `{"error": "Missing tickers or threshold parameter"}`

## Service Mapping
- Handler: `application.services.market.alert_service.handle_alert_query`
- Tool: `handle_alert_query_tool` (in `application.agents.tool_registry`)