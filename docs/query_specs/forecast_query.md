# forecast_query

## Overview
Forecast query projects future stock prices using simple moving average trend extrapolation. Priority: low. Selected when the query contains keywords like "dự báo", "forecast", "dự đoán", "xu hướng", "sắp tới".

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | list[str] | — | Stock tickers to forecast |
| timeframe | No | string | "1w" | Forecast horizon (informational, does not change computation) |
| model | No | string | null | Model name (informational only; always uses simple_moving_average) |

## Input Constraints
- `tickers` must be non-empty
- Requires at least 20 historical data points (`len(data) >= 20`); otherwise returns error per ticker
- `model` parameter is accepted but ignored — the service always uses `simple_moving_average`
- Results are cached per `(ticker, timeframe)` with TTL of 1 hour

## Output Contract

### Success Response
```json
{
  "forecasts": {
    "ticker": {
      "last_price": "float",
      "projected_price": "float",
      "confidence_bounds": {
        "lower": "float",
        "upper": "float"
      },
      "volatility": "float",
      "trend_pct": "float",
      "sma_20": "float",
      "data_points": "int",
      "timeframe": "string"
    }
  },
  "model": "simple_moving_average",
  "timeframe": "string"
}
```

### Error Response
```json
{ "error": "Insufficient historical data for forecast" }
```

## Field Definitions

### Forecast Fields
| Field | Description |
|-------|-------------|
| last_price | Most recent closing price |
| projected_price | last_price * (1 + recent_trend) |
| confidence_bounds.lower | projected_price - (volatility * 1.96) |
| confidence_bounds.upper | projected_price + (volatility * 1.96) |
| volatility | Standard deviation of last 20 closing prices |
| trend_pct | Percentage change over last 5 days |
| sma_20 | Simple moving average of last 20 closing prices |
| data_points | Number of historical data points used |

## Examples

### Example 1: Basic forecast
Input: "Dự báo giá FPT tuần tới"
Parsed: `{"query_type": "forecast_query", "tickers": ["FPT"], "timeframe": "1w"}`
Response: `{"forecasts": {"FPT": {"last_price": 125000.0, "projected_price": 128750.0, "confidence_bounds": {"lower": 121250.0, "upper": 136250.0}, "volatility": 3826.53, "trend_pct": 3.0, "sma_20": 123500.0, "data_points": 252, "timeframe": "1w"}}, "model": "simple_moving_average", "timeframe": "1w"}`

### Example 2: Multiple tickers
Input: "Dự báo giá VNM và HPG 1 tháng"
Parsed: `{"query_type": "forecast_query", "tickers": ["VNM", "HPG"], "timeframe": "1m"}`
Response: `{"forecasts": {"VNM": {"last_price": 70000.0, "projected_price": 69300.0, "confidence_bounds": {"lower": 66500.0, "upper": 72100.0}, "volatility": 1428.57, "trend_pct": -1.0, "sma_20": 69500.0, "data_points": 252, "timeframe": "1m"}, "HPG": {"last_price": 28500.0, "projected_price": 29070.0, "confidence_bounds": {"lower": 27000.0, "upper": 31140.0}, "volatility": 1056.12, "trend_pct": 2.0, "sma_20": 28300.0, "data_points": 252, "timeframe": "1m"}}, "model": "simple_moving_average", "timeframe": "1m"}`

### Example 3: Insufficient data
Input: "Dự báo giá XYZ"
Parsed: `{"query_type": "forecast_query", "tickers": ["XYZ"], "timeframe": "1w"}`
Response: `{"forecasts": {"XYZ": {"error": "Insufficient historical data for forecast"}}, "model": "simple_moving_average", "timeframe": "1w"}`

### Example 4: Missing tickers
Input: "Dự báo thị trường"
Parsed: `{"query_type": "forecast_query"}`
Response: `{"error": "Missing tickers"}`

## Service Mapping
- Handler: `application.services.market.forecast_service.handle_forecast_query`
- Tool: `handle_forecast_query_tool` (in `application.agents.tool_registry`)