# Price Query

## Overview
Retrieves historical trading price data for one or more stock tickers. High priority — this is the most fundamental query type. Selected when the user asks for price, trading data, OHLCV, or historical values without comparison, ranking, or aggregation intent.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | List of stock ticker symbols to query |
| requested_field | No | string | "close" | Data field to retrieve: open, close, volume, ohlcv |
| start | No | string (YYYY-MM-DD) | — | Inclusive start date for data range |
| end | No | string (YYYY-MM-DD) | — | Inclusive end date for data range (defaults to today) |
| days | No | integer | — | Number of days back from today |
| weeks | No | integer | — | Number of weeks back from today |
| months | No | integer | — | Number of months back from today |

## Input Constraints
- At least one ticker must be provided
- Time range must be specified via either (start/end) OR (days/weeks/months). If neither is provided, defaults to a reasonable window.
- Time parameters (days/weeks/months) are mutually exclusive in a single query
- start and end must be used together
- requested_field must be one of: open, close, volume, ohlcv

## Output Contract

### Success Response
```json
{
  "TICKER": [
    { "date": "YYYY-MM-DD", "field_value": number }
  ]
}
```

For `ohlcv`:
```json
{
  "TICKER": [
    { "date": "YYYY-MM-DD", "open": number, "high": number, "low": number, "close": number, "volume": integer }
  ]
}
```

### Error Response
```json
{ "error": "string" }
```

## Field Definitions

### Requested Field Enum
| Value | Description |
|-------|-------------|
| open | Opening price |
| close | Closing price (default) |
| volume | Trading volume |
| ohlcv | Full OHLCV data (open, high, low, close, volume) |

## Examples

### Example 1: Single ticker, close price, 1 day
Input: "Lấy giá mở cửa của VCB hôm qua."
Parsed: `{ "query_type": "price_query", "requested_field": "open", "tickers": ["VCB"], "days": 1 }`
Response: `{ "VCB": [ { "date": "2026-05-12", "open": 45.2 } ] }`

### Example 2: Full OHLCV data
Input: "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất."
Parsed: `{ "query_type": "price_query", "requested_field": "ohlcv", "tickers": ["HPG"], "days": 10 }`
Response: `{ "HPG": [ { "date": "2026-05-01", "open": 28.5, "high": 29.0, "low": 28.3, "close": 28.8, "volume": 1500000 } ] }`

### Example 3: Open price, multiple days
Input: "Giá mở cửa của VIC trong 5 ngày vừa rồi."
Parsed: `{ "query_type": "price_query", "requested_field": "open", "tickers": ["VIC"], "days": 5 }`
Response: `{ "VIC": [ { "date": "2026-05-08", "open": 92.1 }, { "date": "2026-05-09", "open": 91.8 } ] }`

## Service Mapping
- Handler: `src/application/services/market/price_service.py`
- Tool: `handle_price_tool`