# company_query

## Overview
Retrieves company-related data: shareholders, executives, or subsidiaries. Priority: normal. Selected when user asks for shareholder lists, management/leadership teams, or subsidiary/affiliated companies.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | List of stock ticker symbols |
| requested_field | No | string | "shareholders" | Target data type: `shareholders`, `executives`, or `subsidiaries` |

## Input Constraints
- At least one ticker is required
- `requested_field` is case-sensitive and must match one of the enum values exactly
- No time parameters — data is always the latest available snapshot from the data source

## Output Contract

### Success Response — Shareholders
```json
{
  "TICKER": {
    "shareholders": [
      { "type": "major_shareholders", "data": "..." },
      { "type": "top_shareholders", "data": "..." }
    ],
    "total_shareholders": 2
  }
}
```

### Success Response — Executives
```json
{
  "TICKER": {
    "executives": [
      { "type": "management_team", "data": "..." },
      { "type": "board_of_directors", "data": "..." }
    ],
    "total_executives": 2
  }
}
```

### Success Response — Subsidiaries
```json
{
  "TICKER": {
    "subsidiaries": [
      { "type": "subsidiaries", "data": "..." },
      { "type": "affiliated_companies", "data": "..." }
    ],
    "total_subsidiaries": 2
  }
}
```

### Fallback Response (no specific data found)
```json
{
  "TICKER": {
    "company_info": {
      "company_name": "Vietcombank",
      "company_code": "VCB",
      "industry": "Banking",
      "sector": "Financial"
    },
    "note": "Detailed shareholder information not available in current data source"
  }
}
```

### Error Response
```json
{ "error": "Missing ticker" }
```

```json
{ "error": "No company data available" }
```

```json
{ "error": "No valid data found" }
```

## Field Definitions

### Requested Field Enum
| Value | Description |
|-------|-------------|
| `shareholders` | Major/top shareholders and ownership structure |
| `executives` | Management team, board of directors, key personnel |
| `subsidiaries` | Subsidiary companies, affiliated entities, business units |

## Examples

### Example 1: Shareholder query
Input: "Danh sách cổ đông lớn của VCB."
Parsed: `{"query_type": "company_query", "requested_field": "shareholders", "tickers": ["VCB"]}`
Response: `{"VCB": {"shareholders": [{"type": "major_shareholders", "data": "..."}, {"type": "top_shareholders", "data": "..."}], "total_shareholders": 2}}`

### Example 2: Executive query
Input: "Danh sách lãnh đạo đang làm việc tại HPG."
Parsed: `{"query_type": "company_query", "requested_field": "executives", "tickers": ["HPG"]}`
Response: `{"HPG": {"executives": [{"type": "management_team", "data": "..."}], "total_executives": 1}}`

### Example 3: Subsidiary query
Input: "Các công ty con của VHM."
Parsed: `{"query_type": "company_query", "requested_field": "subsidiaries", "tickers": ["VHM"]}`
Response: `{"VHM": {"subsidiaries": [{"type": "subsidiaries", "data": "..."}], "total_subsidiaries": 1}}`

## Service Mapping
- Handler: `src.application.services.company.company_service.handle_company_query`
- Tool: `handle_company_tool`