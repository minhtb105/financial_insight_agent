# Ranking Query

## Overview
Ranks multiple tickers by an aggregated field value (highest/lowest). Medium priority. Selected when user asks "which ticker has the highest/lowest X", "rank by X", or "top/bottom performer" among a group. Requires at least 2 tickers.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | List of stock ticker symbols to rank (minimum 2) |
| requested_field | No | string | "close" | Data field to rank by: open, close, volume |
| aggregate | No | string | "max" | Aggregation function applied to each ticker's data: max, min, mean, latest |
| start | No | string (YYYY-MM-DD) | — | Inclusive start date |
| end | No | string (YYYY-MM-DD) | — | Inclusive end date (defaults to today) |
| days | No | integer | — | Number of days back from today |
| weeks | No | integer | — | Number of weeks back from today |
| months | No | integer | — | Number of months back from today |

## Input Constraints
- At least 2 tickers are required
- Time range via (start/end) OR (days/weeks/months)
- requested_field must be one of: open, close, volume
- aggregate must be one of: max, min, mean, latest
- When aggregate=min, ranking ascends (lowest value = rank 1)
- When aggregate=max, ranking descends (highest value = rank 1)

## Output Contract

### Success Response
```json
{
  "ranking": {
    "ranking_list": [
      { "rank": integer, "ticker": "string", "value": number, "data_points": integer }
    ],
    "top_performer": { "rank": integer, "ticker": "string", "value": number, "data_points": integer },
    "bottom_performer": { "rank": integer, "ticker": "string", "value": number, "data_points": integer },
    "total_tickers": integer,
    "valid_tickers": [ "string" ],
    "statistics": {
      "mean": number,
      "median": number,
      "std_dev": number,
      "range": number
    },
    "field": "string",
    "aggregate": "string"
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
| Value | Description | Sort Order |
|-------|-------------|------------|
| max | Maximum value | Descending (highest = rank 1) |
| min | Minimum value | Ascending (lowest = rank 1) |
| mean | Average value | Descending |
| latest | Most recent value | Descending |

## Examples

### Example 1: Minimum open price
Input: "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?"
Parsed: `{ "query_type": "ranking_query", "requested_field": "open", "tickers": ["VCB", "BID", "CTG"], "aggregate": "min", "days": 1 }`
Response: `{ "ranking": { "ranking_list": [ { "rank": 1, "ticker": "BID", "value": 42.1, "data_points": 1 } ], "top_performer": { "rank": 1, "ticker": "BID", "value": 42.1, "data_points": 1 }, "bottom_performer": { "rank": 3, "ticker": "VCB", "value": 45.2, "data_points": 1 }, "total_tickers": 3, "valid_tickers": ["VCB", "BID", "CTG"], "statistics": { "mean": 43.7, "median": 43.5, "std_dev": 1.3, "range": 3.1 }, "field": "open", "aggregate": "min" } }`

### Example 2: Maximum close price, 10 days
Input: "Mã nào cao nhất trong nhóm VHM, VIC, VRE trong 10 ngày qua?"
Parsed: `{ "query_type": "ranking_query", "requested_field": "close", "tickers": ["VHM", "VIC", "VRE"], "aggregate": "max", "days": 10 }`
Response: `{ "ranking": { "ranking_list": [ { "rank": 1, "ticker": "VIC", "value": 95.0, "data_points": 10 } ] } }`

### Example 3: Minimum volume, 1 week
Input: "Trong nhóm HPG, NKG, HSG mã nào có volume thấp nhất tuần này?"
Parsed: `{ "query_type": "ranking_query", "requested_field": "volume", "tickers": ["HPG", "NKG", "HSG"], "aggregate": "min", "weeks": 1 }`

### Example 4: Maximum close, 1 month
Input: "Trong các mã HSG, HPG, NKG mã nào tăng mạnh nhất trong tháng?"
Parsed: `{ "query_type": "ranking_query", "requested_field": "close", "tickers": ["HSG", "HPG", "NKG"], "aggregate": "max", "months": 1 }`

## Service Mapping
- Handler: `src/application/services/financial/ranking_service.py`
- Tool: `handle_ranking_tool`