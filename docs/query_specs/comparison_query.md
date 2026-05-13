# Comparison Query

## Overview
Compares price data between two groups of tickers (main vs compare). Medium priority. Selected when user asks to "compare X with Y", "so sánh X với Y", or expresses a comparative analysis between two sets of stocks.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | Main group of stock ticker symbols |
| compare_with | Yes | string[] | — | Comparison group of stock ticker symbols |
| requested_field | No | string | "close" | Data field to compare: open, close, volume |
| start | No | string (YYYY-MM-DD) | — | Inclusive start date |
| end | No | string (YYYY-MM-DD) | — | Inclusive end date (defaults to today) |
| days | No | integer | — | Number of days back from today |
| weeks | No | integer | — | Number of weeks back from today |
| months | No | integer | — | Number of months back from today |

## Input Constraints
- Both `tickers` and `compare_with` groups must be non-empty
- Time range via (start/end) OR (days/weeks/months)
- requested_field must be one of: open, close, volume

## Output Contract

### Success Response
```json
{
  "comparison": {
    "main_tickers_stats": {
      "TICKER": { "mean": number, "min": number, "max": number, "latest": number, "count": integer }
    },
    "compare_tickers_stats": {
      "TICKER": { "mean": number, "min": number, "max": number, "latest": number, "count": integer }
    },
    "main_overall": {
      "mean": number,
      "min": number,
      "max": number,
      "latest_mean": number,
      "tickers_count": integer,
      "total_data_points": integer
    },
    "compare_overall": {
      "mean": number,
      "min": number,
      "max": number,
      "latest_mean": number,
      "tickers_count": integer,
      "total_data_points": integer
    },
    "percentage_difference": {
      "mean": { "main": number, "compare": number, "difference": number, "percentage": number },
      "min": { "main": number, "compare": number, "difference": number, "percentage": number },
      "max": { "main": number, "compare": number, "difference": number, "percentage": number },
      "latest_mean": { "main": number, "compare": number, "difference": number, "percentage": number }
    },
    "field": "string"
  },
  "main_tickers": [ "string" ],
  "compare_tickers": [ "string" ],
  "requested_field": "string",
  "time_range": { "start_date": "string", "end_date": "string" }
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

## Examples

### Example 1: Volume comparison, 1 week
Input: "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần."
Parsed: `{ "query_type": "comparison_query", "requested_field": "volume", "tickers": ["VIC"], "compare_with": ["HPG"], "weeks": 1 }`
Response: `{ "comparison": { "main_tickers_stats": { "VIC": { "mean": 1200000, "min": 800000, "max": 1500000, "latest": 1400000, "count": 5 } }, "compare_tickers_stats": { "HPG": { "mean": 2500000, "min": 2000000, "max": 3100000, "latest": 2800000, "count": 5 } }, "main_overall": { "mean": 1200000, "min": 800000, "max": 1500000, "latest_mean": 1400000, "tickers_count": 1, "total_data_points": 5 }, "compare_overall": { "mean": 2500000, "min": 2000000, "max": 3100000, "latest_mean": 2800000, "tickers_count": 1, "total_data_points": 5 }, "percentage_difference": { "mean": { "main": 1200000, "compare": 2500000, "difference": -1300000, "percentage": -52.0 }, "min": { "main": 800000, "compare": 2000000, "difference": -1200000, "percentage": -60.0 }, "max": { "main": 1500000, "compare": 3100000, "difference": -1600000, "percentage": -51.6 }, "latest_mean": { "main": 1400000, "compare": 2800000, "difference": -1400000, "percentage": -50.0 } }, "field": "volume" } }`

### Example 2: Close price comparison, 1 day
Input: "So sánh giá đóng của VCB với BID hôm nay."
Parsed: `{ "query_type": "comparison_query", "requested_field": "close", "tickers": ["VCB"], "compare_with": ["BID"], "days": 1 }`
Response: `{ "comparison": { "main_tickers_stats": { "VCB": { "mean": 45.2, "min": 45.2, "max": 45.2, "latest": 45.2, "count": 1 } }, "compare_tickers_stats": { "BID": { "mean": 42.1, "min": 42.1, "max": 42.1, "latest": 42.1, "count": 1 } } } }`

## Service Mapping
- Handler: `src/application/services/market/compare_service.py`
- Tool: `handle_compare_tool`