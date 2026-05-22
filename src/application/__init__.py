__all__ = [
    "build_graph",
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
        "build_graph": ".agents.agent",
        "handle_price_query": ".services.market.price_service",
        "handle_indicator_query": ".services.market.indicator_service",
        "handle_compare_query": ".services.market.compare_service",
        "handle_alert_query": ".services.market.alert_service",
        "handle_forecast_query": ".services.market.forecast_service",
        "handle_sector_query": ".services.market.sector_service",
        "handle_company_query": ".services.company.company_service",
        "handle_financial_ratio_query": ".services.financial.financial_ratio_service",
        "handle_aggregate_query": ".services.financial.aggregate_service",
        "handle_ranking_query": ".services.financial.ranking_service",
        "handle_news_sentiment_query": ".services.portfolio.news_sentiment_service",
        "handle_portfolio_query": ".services.portfolio.portfolio_service",
    }
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
