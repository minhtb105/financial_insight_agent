# Query Type Specs

Central contracts for all financial query types. Each spec defines the exact input/output contract for one query type.

## Purpose

Eliminate schema drift between:
- User query → Parser output (parsed dict)
- Parser output → Service handler input
- Service handler → Response output
- Tool description → Actual behavior

## Pipeline

```
docs/query_specs/*.md  →  domain/schemas/*.py  →  prompt injection  →  type validation  →  test generation
     contracts               Pydantic models          LLM prompts         guardrails            drift detect
```

## Spec Files

| # | Type | Doc | Service |
|---|------|-----|---------|
| 1 | `price_query` | [price_query.md](price_query.md) | `services/market/price_service.py` |
| 2 | `ranking_query` | [ranking_query.md](ranking_query.md) | `services/financial/ranking_service.py` |
| 3 | `comparison_query` | [comparison_query.md](comparison_query.md) | `services/market/compare_service.py` |
| 4 | `aggregate_query` | [aggregate_query.md](aggregate_query.md) | `services/financial/aggregate_service.py` |
| 5 | `indicator_query` | [indicator_query.md](indicator_query.md) | `services/market/indicator_service.py` |
| 6 | `company_query` | [company_query.md](company_query.md) | `services/company/company_service.py` |
| 7 | `financial_ratio_query` | [financial_ratio_query.md](financial_ratio_query.md) | `services/financial/financial_ratio_service.py` |
| 8 | `news_sentiment_query` | [news_sentiment_query.md](news_sentiment_query.md) | `services/portfolio/news_sentiment_service.py` |
| 9 | `portfolio_query` | [portfolio_query.md](portfolio_query.md) | `services/portfolio/portfolio_service.py` |
| 10 | `alert_query` | [alert_query.md](alert_query.md) | `services/market/alert_service.py` |
| 11 | `forecast_query` | [forecast_query.md](forecast_query.md) | `services/market/forecast_service.py` |
| 12 | `sector_query` | [sector_query.md](sector_query.md) | `services/market/sector_service.py` |

## Drift Detection

When modifying any component, check ALL layers:

1. **Spec doc** → does the contract need updating?
2. **Pydantic schema** → does `domain/schemas/{type}.py` match the spec?
3. **Prompt** → does `nlp_parser.py` prompt reflect current schema?
4. **Guardrails** → does `type_validators.py` enforce the spec?
5. **Tests** → does `tests/spec_drift/` test the new contract?

## Changelog

| Date | Change |
|------|--------|
| 2026-05-13 | Initial spec creation for all 12 query types |