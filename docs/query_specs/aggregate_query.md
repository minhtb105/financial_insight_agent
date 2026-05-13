# Aggregate Query

## Overview
Computes a cross-ticker aggregation function (mean, sum, median, std, min, max) over a group of stocks. Low-medium priority. Selected when user asks "total X", "average X", "sum of X", "X trung bình", "tổng X" across multiple tickers. Requires at least 2 tickers.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | List of stock ticker symbols to aggregate (minimum 2) |
| requested_field | No | string | "close" | Data field to aggregate: open, close, volume |
| aggregate | No | string | "mean" | Aggregation function: mean, sum, median, std, min, max |
| start | No | string (YYYY-MM-DD) | — | Inclusive start date |
| end | No | string (YYYY-MM-DD) | — | Inclusive end date (defaults to today) |
| days | No | integer | — | Number of days back from today |
| weeks | No | integer | — | Number of weeks back from today |
| months | No | integer | — | Number of months back from today |

## Input Constraints
- At least 2 tickers are required
- Time range via (start/end) OR (days/weeks/months)
- requested_field must be one of: open, close, volume
- aggregate must be one of: mean, sum, median, std, min, max

## Output Contract

### Success Response
```json
{
  "aggregation": {
    "result": {
      "function": "string",
      "value": number,
      "field": "string"
    },
    "overall_statistics": {
      "mean": number,
      "median": number,
      "std_dev": number,
      "min": number,
      "max": number,
      "sum": number,
      "coefficient_of_variation": number,
      "total_data_points": integer
    },
    "ticker_breakdown": {
      "TICKER": {
        "values": [ number ],
        "count": integer,
        "mean": number,
        "min": number,
        "max": number
      }
    },
    "valid_tickers": [ "string" ],
    "total_tickers": integer
  },
  "tickers": [ "string" ],
  "requested_field": "string",
  "aggregate": "string",
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

### Aggregate Enum
| Value | Description |
|-------|-------------|
| mean | Arithmetic mean of all values across all tickers (default) |
| sum | Sum of all values across all tickers |
| median | Median of all values across all tickers |
| std | Standard deviation of all values across all tickers |
| min | Minimum value across all tickers |
| max | Maximum value across all tickers |

## Examples

### Example 1: Sum volume, 1 week
Input: "Tổng khối lượng giao dịch của HPG trong 1 tuần."
Parsed: `{ "query_type": "aggregate_query", "requested_field": "volume", "tickers": ["HPG"], "aggregate": "sum", "weeks": 1 }`
Response: `{ "aggregation": { "result": { "function": "sum", "value": 12500000, "field": "volume" }, "overall_statistics": { "mean": 2500000, "median": 2400000, "std_dev": 500000, "min": 2000000, "max": 3100000, "sum": 12500000, "coefficient_of_variation": 20.0, "total_data_points": 5 }, "ticker_breakdown": { "HPG": { "values": [ 2000000, 2400000, 3100000, 2500000, 2500000 ], "count": 5, "mean": 2500000, "min": 2000000, "max": 3100000 } }, "valid_tickers": ["HPG"], "total_tickers": 1 } }`

### Example 2: Mean close price, 10 days
Input: "Giá đóng trung bình của VCB trong 10 ngày."
Parsed: `{ "query_type": "aggregate_query", "requested_field": "close", "tickers": ["VCB"], "aggregate": "mean", "days": 10 }`

### Example 3: Min close price, current month
Input: "Cho tôi giá đóng nhỏ nhất của SSI từ đầu tháng."
Parsed: `{ "query_type": "aggregate_query", "requested_field": "close", "tickers": ["SSI"], "aggregate": "min" }`

## Service Mapping
- Handler: `src/application/services/financial/aggregate_service.py`
- Tool: `handle_aggregate_tool`