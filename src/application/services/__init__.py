__all__ = [
    "handle_aggregate_query",
    "handle_alert_query",
    "handle_company_query",
    "handle_compare_query",
    "handle_financial_ratio_query",
    "handle_forecast_query",
    "handle_indicator_query",
    "handle_news_sentiment_query",
    "handle_portfolio_query",
    "handle_price_query",
    "handle_ranking_query",
    "handle_sector_query",
]


def __getattr__(name):
    import importlib

    _LAZY = {
        "handle_price_query": ".market.price_service",
        "handle_indicator_query": ".market.indicator_service",
        "handle_compare_query": ".market.compare_service",
        "handle_alert_query": ".market.alert_service",
        "handle_forecast_query": ".market.forecast_service",
        "handle_sector_query": ".market.sector_service",
        "handle_company_query": ".company.company_service",
        "handle_financial_ratio_query": ".financial.financial_ratio_service",
        "handle_aggregate_query": ".financial.aggregate_service",
        "handle_ranking_query": ".financial.ranking_service",
        "handle_news_sentiment_query": ".portfolio.news_sentiment_service",
        "handle_portfolio_query": ".portfolio.portfolio_service",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
