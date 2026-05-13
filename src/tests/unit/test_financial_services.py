"""
Unit tests for financial services.
Uses relative imports for proper module resolution.
"""

from application.services.financial.financial_ratio_service import handle_financial_ratio_query
from application.services.financial.aggregate_service import handle_aggregate_query
from application.services.financial.ranking_service import handle_ranking_query


def test_financial_ratio_pe():
    test_cases = [
        {"ticker": "VNM", "ratio": "pe"},
        {"ticker": "HPG", "ratio": "pe"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "financial_ratio_query",
            "requested_field": tc["ratio"],
            "tickers": [tc["ticker"]],
        }
        result = handle_financial_ratio_query(parsed)
        assert result is not None


def test_financial_ratio_roe():
    test_cases = [
        {"ticker": "VNM", "ratio": "roe"},
        {"ticker": "HPG", "ratio": "roe"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "financial_ratio_query",
            "requested_field": tc["ratio"],
            "tickers": [tc["ticker"]],
        }
        result = handle_financial_ratio_query(parsed)
        assert result is not None


def test_financial_ratio_eps():
    test_cases = [
        {"ticker": "VNM", "ratio": "eps"},
        {"ticker": "HPG", "ratio": "eps"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "financial_ratio_query",
            "requested_field": tc["ratio"],
            "tickers": [tc["ticker"]],
        }
        result = handle_financial_ratio_query(parsed)
        assert result is not None


def test_financial_ratio_empty_tickers():
    parsed = {
        "query_type": "financial_ratio_query",
        "requested_field": "pe",
        "tickers": [],
    }
    result = handle_financial_ratio_query(parsed)
    assert result is not None


def test_aggregate_market_cap():
    test_cases = [
        {"ticker": "VNM"},
        {"ticker": "HPG"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "aggregate_query",
            "requested_field": "market_cap",
            "tickers": [tc["ticker"]],
        }
        result = handle_aggregate_query(parsed)
        assert result is not None


def test_aggregate_beta():
    test_cases = [
        {"ticker": "VNM"},
        {"ticker": "HPG"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "aggregate_query",
            "requested_field": "beta",
            "tickers": [tc["ticker"]],
        }
        result = handle_aggregate_query(parsed)
        assert result is not None


def test_aggregate_dividend_yield():
    test_cases = [
        {"ticker": "VNM"},
        {"ticker": "HPG"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "aggregate_query",
            "requested_field": "dividend_yield",
            "tickers": [tc["ticker"]],
        }
        result = handle_aggregate_query(parsed)
        assert result is not None


def test_aggregate_empty_tickers():
    parsed = {
        "query_type": "aggregate_query",
        "requested_field": "market_cap",
        "tickers": [],
    }
    result = handle_aggregate_query(parsed)
    assert result is not None


def test_ranking_by_performance():
    test_cases = [
        {"tickers": ["VNM", "HPG", "VIC"], "time_range": "1 tuần"},
        {"tickers": ["VCB", "BID", "CTG"], "time_range": "1 tháng"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "ranking_query",
            "requested_field": "performance",
            "tickers": tc["tickers"],
            "time_range": tc["time_range"],
        }
        result = handle_ranking_query(parsed)
        assert result is not None


def test_ranking_by_volume():
    test_cases = [
        {"tickers": ["VNM", "HPG", "VIC"], "time_range": "1 tuần"},
        {"tickers": ["VCB", "BID", "CTG"], "time_range": "1 tháng"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "ranking_query",
            "requested_field": "volume",
            "tickers": tc["tickers"],
            "time_range": tc["time_range"],
        }
        result = handle_ranking_query(parsed)
        assert result is not None


def test_ranking_by_market_cap():
    test_cases = [
        {"tickers": ["VNM", "HPG", "VIC"]},
        {"tickers": ["VCB", "BID", "CTG"]},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "ranking_query",
            "requested_field": "market_cap",
            "tickers": tc["tickers"],
        }
        result = handle_ranking_query(parsed)
        assert result is not None


def test_ranking_empty_tickers():
    parsed = {
        "query_type": "ranking_query",
        "requested_field": "performance",
        "tickers": [],
    }
    result = handle_ranking_query(parsed)
    assert result is not None


if __name__ == "__main__":
    test_financial_ratio_pe()
    test_financial_ratio_roe()
    test_financial_ratio_eps()
    test_financial_ratio_empty_tickers()
    test_aggregate_market_cap()
    test_aggregate_beta()
    test_aggregate_dividend_yield()
    test_aggregate_empty_tickers()
    test_ranking_by_performance()
    test_ranking_by_volume()
    test_ranking_by_market_cap()
    test_ranking_empty_tickers()
    print("All financial service tests passed!")