# portfolio_query

## Overview
Portfolio query retrieves portfolio value, performance, or sector allocation data. Priority: medium. Selected when the query contains keywords like "danh mục", "portfolio", "hiệu suất", "phân bổ", "giá trị".

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| requested_field | No | string | null | Sub-query selector: portfolio_value, portfolio_performance, portfolio_allocation. Returns all combined if null. |
| portfolio | No | dict[str, int] | null | Ticker-to-quantity mapping to temporarily add to holdings |
| tickers | No | list[str] | null | Deprecated; portfolio overrides this |

## Input Constraints
- If `requested_field` is null, all three sub-queries are executed and merged into one response
- `portfolio` values are **temporarily merged** with persisted holdings (from user_portfolio.json) — they do not persist after the query
- `requested_field` is case-insensitive; recognized values: `portfolio_value`, `portfolio_performance`, `portfolio_allocation`

## Output Contract

### Success Response

#### Portfolio Value (requested_field = "portfolio_value")
```json
{
  "portfolio_value": "float",
  "holdings": {
    "ticker": {
      "quantity": "int",
      "current_price": "float",
      "value": "float"
    }
  }
}
```

#### Portfolio Performance (requested_field = "portfolio_performance")
```json
{
  "total_invested": "float",
  "current_value": "float",
  "total_return": "float",
  "return_rate": "float"
}
```

#### Portfolio Allocation (requested_field = "portfolio_allocation")
```json
{
  "allocation": {
    "sector_name": {
      "value": "float",
      "percentage": "float"
    }
  },
  "diversification_score": "int",
  "total_value": "float"
}
```

#### Combined (requested_field = null)
```json
{
  "portfolio_value": {
    "portfolio_value": "float",
    "holdings": { "ticker": { "quantity": "int", "current_price": "float", "value": "float" } }
  },
  "portfolio_performance": {
    "total_invested": "float",
    "current_value": "float",
    "total_return": "float",
    "return_rate": "float"
  },
  "portfolio_allocation": {
    "allocation": { "sector_name": { "value": "float", "percentage": "float" } },
    "diversification_score": "int",
    "total_value": "float"
  }
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
| portfolio_value | Current market value of all holdings |
| portfolio_performance | Return on investment and profit/loss metrics |
| portfolio_allocation | Sector breakdown and diversification score |
| null | Return all three combined |

## Examples

### Example 1: Basic value query
Input: "Giá trị danh mục hiện tại của tôi là bao nhiêu?"
Parsed: `{"query_type": "portfolio_query", "requested_field": "portfolio_value"}`
Response: `{"portfolio_value": 152500000, "holdings": {"FPT": {"quantity": 100, "current_price": 125000, "value": 12500000}, "VNM": {"quantity": 200, "current_price": 70000, "value": 14000000}}}`

### Example 2: Add holdings and get performance
Input: "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì hiệu suất danh mục ra sao?"
Parsed: `{"query_type": "portfolio_query", "requested_field": "portfolio_performance", "portfolio": {"FPT": 100, "VNM": 200}}`
Response: `{"total_invested": 26500000, "current_value": 28500000, "total_return": 2000000, "return_rate": 7.55}`

### Example 3: Sector allocation
Input: "Phân bổ ngành trong danh mục hiện tại"
Parsed: `{"query_type": "portfolio_query", "requested_field": "portfolio_allocation"}`
Response: `{"allocation": {"Công nghệ": {"value": 12500000, "percentage": 47.17}, "Thực phẩm": {"value": 14000000, "percentage": 52.83}}, "diversification_score": 50, "total_value": 26500000}`

### Example 4: Empty portfolio
Input: "Giá trị danh mục?"
Parsed: `{"query_type": "portfolio_query", "requested_field": "portfolio_value"}`
Response: `{"portfolio_value": 0, "holdings": {}}`

### Example 5: No portfolio data found
Input: "Tổng quan danh mục"
Parsed: `{"query_type": "portfolio_query", "requested_field": null}`
Response: `{"error": "No portfolio data found"}`

## Service Mapping
- Handler: `application.services.portfolio.portfolio_service.handle_portfolio_query`
- Tool: `handle_portfolio_query_tool` (in `application.agents.tool_registry`)