"""
Unit tests for market services.
Uses relative imports for proper module resolution.
"""

from application.services.market.compare_service import handle_compare_query
from application.services.market.indicator_service import handle_indicator_query
from application.services.market.price_service import handle_price_query


def test_compare_two_stocks():
    test_cases = [
        {
            "ticker1": "VNM",
            "ticker2": "HPG",
            "metrics": ["price", "volume"],
            "time_range": "1 tuần",
        },
        {
            "ticker1": "VCB",
            "ticker2": "BID",
            "metrics": ["close", "volume"],
            "time_range": "1 tháng",
        },
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "comparison_query",
            "tickers": [tc["ticker1"], tc["ticker2"]],
            "compare_with": tc["ticker2"],
            "metrics": tc["metrics"],
            "time_range": tc["time_range"],
        }
        result = handle_compare_query(parsed)
        assert result is not None


def test_compare_multiple_stocks():
    test_cases = [
        {
            "tickers": ["VNM", "HPG", "VIC"],
            "metrics": ["price", "volume"],
            "time_range": "1 tuần",
        },
        {
            "tickers": ["VCB", "BID", "CTG"],
            "metrics": ["close", "volume"],
            "time_range": "1 tháng",
        },
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "comparison_query",
            "tickers": tc["tickers"],
            "metrics": tc["metrics"],
            "time_range": tc["time_range"],
        }
        result = handle_compare_query(parsed)
        assert result is not None


def test_compare_with_metrics():
    test_cases = [
        {
            "tickers": ["VNM", "HPG"],
            "metrics": ["price_change", "volume_change"],
            "time_range": "1 tuần",
        },
        {
            "tickers": ["VCB", "BID"],
            "metrics": ["close_change", "volume_change"],
            "time_range": "1 tháng",
        },
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "comparison_query",
            "tickers": tc["tickers"],
            "metrics": tc["metrics"],
            "time_range": tc["time_range"],
        }
        result = handle_compare_query(parsed)
        assert result is not None


def test_compare_empty_tickers():
    parsed = {
        "query_type": "comparison_query",
        "tickers": [],
        "metrics": ["price"],
        "time_range": "1 tuần",
    }
    result = handle_compare_query(parsed)
    assert result is not None


def test_indicator_bollinger_bands():
    test_cases = [
        {"ticker": "VNM", "period": 20, "indicator": "bollinger_bands"},
        {"ticker": "HPG", "period": 14, "indicator": "bollinger_bands"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "indicator_query",
            "requested_field": tc["indicator"],
            "tickers": [tc["ticker"]],
        }
        result = handle_indicator_query(parsed)
        assert result is not None


def test_indicator_stochastic():
    test_cases = [
        {"ticker": "VNM", "indicator": "stochastic"},
        {"ticker": "HPG", "indicator": "stochastic"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "indicator_query",
            "requested_field": tc["indicator"],
            "tickers": [tc["ticker"]],
        }
        result = handle_indicator_query(parsed)
        assert result is not None


def test_indicator_adx():
    test_cases = [
        {"ticker": "VNM", "period": 14, "indicator": "adx"},
        {"ticker": "HPG", "period": 20, "indicator": "adx"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "indicator_query",
            "requested_field": tc["indicator"],
            "tickers": [tc["ticker"]],
        }
        result = handle_indicator_query(parsed)
        assert result is not None


def test_indicator_atr():
    test_cases = [
        {"ticker": "VNM", "period": 14, "indicator": "atr"},
        {"ticker": "HPG", "period": 20, "indicator": "atr"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "indicator_query",
            "requested_field": tc["indicator"],
            "tickers": [tc["ticker"]],
        }
        result = handle_indicator_query(parsed)
        assert result is not None


def test_indicator_empty_ticker():
    parsed = {
        "query_type": "indicator_query",
        "requested_field": "bollinger_bands",
        "tickers": [],
    }
    result = handle_indicator_query(parsed)
    assert result is not None


def test_price_ohlcv():
    test_cases = [
        {"ticker": "VNM", "time_range": "1 tuần"},
        {"ticker": "HPG", "time_range": "1 tháng"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "price_query",
            "requested_field": "ohlcv",
            "tickers": [tc["ticker"]],
            "time_range": tc["time_range"],
        }
        result = handle_price_query(parsed)
        assert result is not None


def test_price_history():
    test_cases = [
        {"ticker": "VNM", "time_range": "1 tuần"},
        {"ticker": "HPG", "time_range": "1 tháng"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "price_query",
            "requested_field": "history",
            "tickers": [tc["ticker"]],
            "time_range": tc["time_range"],
        }
        result = handle_price_query(parsed)
        assert result is not None


def test_price_latest():
    test_cases = [
        {"ticker": "VNM"},
        {"ticker": "HPG"},
    ]

    for tc in test_cases:
        parsed = {
            "query_type": "price_query",
            "requested_field": "latest_price",
            "tickers": [tc["ticker"]],
        }
        result = handle_price_query(parsed)
        assert result is not None
        assert isinstance(result, dict)
        assert "latest_price" in result or "price" in result


def test_price_empty_ticker():
    parsed = {
        "query_type": "price_query",
        "requested_field": "latest_price",
        "tickers": [],
    }
    result = handle_price_query(parsed)
    assert result is not None


if __name__ == "__main__":
    test_compare_two_stocks()
    test_compare_multiple_stocks()
    test_compare_with_metrics()
    test_compare_empty_tickers()
    test_indicator_bollinger_bands()
    test_indicator_stochastic()
    test_indicator_adx()
    test_indicator_atr()
    test_indicator_empty_ticker()
    test_price_ohlcv()
    test_price_history()
    test_price_latest()
    test_price_empty_ticker()
    print("All market service tests passed!")