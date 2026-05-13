# news_sentiment_query

## Overview
Retrieves news articles, sentiment scores, and social volume data for tickers. Priority: normal. Selected when user asks for latest news, market sentiment, social media buzz, or positive/negative news about stocks.

## Input Contract

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| tickers | Yes | string[] | — | List of stock ticker symbols |
| requested_field | No | string | — | Data type: `news`, `sentiment`, `social_volume`, `positive_news`, `negative_news`, or omitted for combined |
| compare_with | No | string[] | — | Tickers to compare sentiment against (single ticker + sentiment only) |
| days | No | int | 7 | Lookback days |
| weeks | No | int | — | Lookback weeks (overrides `days` as `weeks * 7`) |
| months | No | int | — | Lookback months (overrides `days` as `months * 30`) |

## Input Constraints
- At least one ticker is required
- `compare_with` is only supported when `requested_field` is `"sentiment"` AND `tickers` has exactly one element
- If `requested_field` is omitted, the handler returns combined data (news + sentiment + social_volume)
- `positive_news` and `negative_news` currently behave the same as `news` at the service layer (no separate filtering implemented)

## Output Contract

### Success Response — News
```json
{
  "VCB": [
    { "title": "...", "content": "...", "date": "...", "source": "..." }
  ]
}
```

### Success Response — Sentiment
```json
{
  "VCB": 0.75,
  "BID": 0.30
}
```

### Success Response — Social Volume
```json
{
  "VCB": 100,
  "HPG": 100
}
```

### Success Response — Combined
```json
{
  "VCB": {
    "news": [{ "title": "...", "content": "...", "date": "...", "source": "..." }],
    "sentiment": 0.75,
    "social_volume": 100
  }
}
```

### Success Response — Comparison
```json
{
  "VCB": 0.75,
  "BID": 0.30,
  "MBB": 0.60
}
```

### Error Response
```json
{ "error": "Missing ticker" }
```

```json
{ "error": "Comparison only supported for sentiment field" }
```

## Field Definitions

### Requested Field Enum
| Value | Output Type | Description |
|-------|-------------|-------------|
| `news` | `dict[ticker -> list]` | Raw news articles for each ticker |
| `sentiment` | `dict[ticker -> float]` | Aggregate sentiment score (-1.0 to 1.0) |
| `social_volume` | `dict[ticker -> int]` | Social media mention count |
| `positive_news` | `dict[ticker -> list]` | Positive news (same as `news` at current service layer) |
| `negative_news` | `dict[ticker -> list]` | Negative news (same as `news` at current service layer) |
| *omitted* | `dict[ticker -> {news, sentiment, social_volume}]` | Combined response |

## Examples

### Example 1: News query
Input: "Có tin tức gì về VCB trong tuần này không?"
Parsed: `{"query_type": "news_sentiment_query", "requested_field": "news", "tickers": ["VCB"], "weeks": 1}`
Response: `{"VCB": [{"title": "...", "content": "...", "date": "2024-01-05", "source": "..."}]}`

### Example 2: Sentiment for multiple tickers
Input: "Cảm xúc thị trường đối với nhóm ngân hàng hiện nay ra sao?"
Parsed: `{"query_type": "news_sentiment_query", "requested_field": "sentiment", "tickers": ["VCB", "BID", "CTG", "MBB", "ACB"], "days": 7}`
Response: `{"VCB": 0.75, "BID": 0.30, "CTG": 0.60, "MBB": 0.55, "ACB": 0.65}`

### Example 3: Positive news
Input: "Tin tức tích cực về FPT trong tháng 11"
Parsed: `{"query_type": "news_sentiment_query", "requested_field": "positive_news", "tickers": ["FPT"], "months": 1}`
Response: `{"FPT": [{"title": "...", "content": "...", "date": "2024-11-15", "source": "..."}]}`

## Service Mapping
- Handler: `src.application.services.portfolio.news_sentiment_service.handle_news_sentiment_query`
- Tool: `handle_news_sentiment_tool`