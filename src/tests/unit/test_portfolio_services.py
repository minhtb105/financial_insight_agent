"""
Unit tests for portfolio services.
Uses relative imports for proper module resolution.
"""

from application.services.portfolio.news_sentiment_service import handle_news_sentiment_query
from application.services.portfolio.portfolio_service import handle_portfolio_query


def test_news_sentiment_query():
    test_cases = [
        {
            "ticker": "VNM",
            "time_range": "1 tuần",
        },
        {
            "ticker": "HPG",
            "time_range": "1 tháng",
        },
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "news_sentiment_query",
            "requested_field": "news",
            "tickers": [tc["ticker"]],
            "time_range": tc["time_range"],
        }
        result = handle_news_sentiment_query(parsed)
        assert result is not None


def test_news_sentiment_with_empty_tickers():
    parsed = {
        "query_type": "news_sentiment_query",
        "requested_field": "news",
        "tickers": [],
        "time_range": "1 tuần",
    }
    result = handle_news_sentiment_query(parsed)
    assert result is not None


def test_sector_sentiment_query():
    test_cases = [
        {"sector": "ngân hàng", "time_range": "1 tuần"},
        {"sector": "bất động sản", "time_range": "1 tháng"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "news_sentiment_query",
            "requested_field": "sector",
            "tickers": [],
            "time_range": tc["time_range"],
            "sector": tc["sector"],
        }
        result = handle_news_sentiment_query(parsed)
        assert result is not None


def test_market_sentiment_query():
    test_cases = [
        {"time_range": "1 tuần"},
        {"time_range": "1 tháng"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "news_sentiment_query",
            "requested_field": "market",
            "tickers": [],
            "time_range": tc["time_range"],
        }
        result = handle_news_sentiment_query(parsed)
        assert result is not None


def test_portfolio_performance_query():
    test_cases = [
        {
            "portfolio": {"VNM": 100, "HPG": 200, "VIC": 50},
            "time_range": "1 tuần",
        },
        {
            "portfolio": {"VCB": 150, "BID": 100, "CTG": 75},
            "time_range": "1 tháng",
        },
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "portfolio_query",
            "requested_field": "performance",
            "tickers": list(tc["portfolio"].keys()),
            "portfolio": tc["portfolio"],
            "time_range": tc["time_range"],
        }
        result = handle_portfolio_query(parsed)
        assert result is not None


def test_portfolio_allocation_query():
    test_cases = [
        {"portfolio": {"VNM": 100, "HPG": 200, "VIC": 50}},
        {"portfolio": {"VCB": 150, "BID": 100, "CTG": 75}},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "portfolio_query",
            "requested_field": "allocation",
            "tickers": list(tc["portfolio"].keys()),
            "portfolio": tc["portfolio"],
        }
        result = handle_portfolio_query(parsed)
        assert result is not None


def test_portfolio_holdings_query():
    test_cases = [
        {"portfolio": {"VNM": 100, "HPG": 200, "VIC": 50}},
        {"portfolio": {"VCB": 150, "BID": 100, "CTG": 75}},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "portfolio_query",
            "requested_field": "holdings",
            "tickers": list(tc["portfolio"].keys()),
            "portfolio": tc["portfolio"],
        }
        result = handle_portfolio_query(parsed)
        assert result is not None


def test_portfolio_with_empty_portfolio():
    parsed = {
        "query_type": "portfolio_query",
        "requested_field": "holdings",
        "tickers": [],
        "portfolio": {},
    }
    result = handle_portfolio_query(parsed)
    assert result is not None


if __name__ == "__main__":
    test_news_sentiment_query()
    test_news_sentiment_with_empty_tickers()
    test_sector_sentiment_query()
    test_market_sentiment_query()
    test_portfolio_performance_query()
    test_portfolio_allocation_query()
    test_portfolio_holdings_query()
    test_portfolio_with_empty_portfolio()
    print("All portfolio service tests passed!")