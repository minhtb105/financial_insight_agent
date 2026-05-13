import pytest
from infrastructure.guardrails.type_validators import validate_parsed_query


class TestValidateParsedQuery:
    def test_valid_price_query(self):
        err = validate_parsed_query({"query_type": "price_query", "tickers": ["VCB"]})
        assert err is None

    def test_invalid_price_query_no_tickers(self):
        err = validate_parsed_query({"query_type": "price_query", "tickers": []})
        assert err is not None

    def test_valid_ranking_query(self):
        err = validate_parsed_query({"query_type": "ranking_query", "tickers": ["VCB", "HPG"]})
        assert err is None

    def test_invalid_ranking_query_single_ticker(self):
        err = validate_parsed_query({"query_type": "ranking_query", "tickers": ["VCB"]})
        assert err is not None

    def test_valid_alert_query(self):
        err = validate_parsed_query({"query_type": "alert_query", "tickers": ["VCB"], "threshold": 100000.0})
        assert err is None

    def test_invalid_alert_query_missing_threshold(self):
        err = validate_parsed_query({"query_type": "alert_query", "tickers": ["VCB"]})
        assert err is not None

    def test_valid_sector_query(self):
        err = validate_parsed_query({"query_type": "sector_query", "sector": "banking"})
        assert err is None

    def test_valid_portfolio_query_empty(self):
        err = validate_parsed_query({"query_type": "portfolio_query"})
        assert err is None

    def test_unknown_query_type(self):
        err = validate_parsed_query({"query_type": "unknown_type"})
        assert err is not None
        assert "unknown" in err.lower()