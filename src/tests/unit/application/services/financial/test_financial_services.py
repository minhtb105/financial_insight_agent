"""Unit tests for financial services — ratio, ranking, aggregation, and helpers."""

from unittest.mock import patch, MagicMock

# -- _ensure_float -------------------------------------------------------


def test_ensure_float_with_none():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float(None) == 0.0


def test_ensure_float_with_float():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float(42.5) == 42.5


def test_ensure_float_with_nan():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float(float("nan"), default=-1) == -1


def test_ensure_float_with_string():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float("3.14") == 3.14


def test_ensure_float_with_invalid_string():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float("abc") == 0.0


def test_ensure_float_with_int():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float(5) == 5.0


def test_ensure_float_with_zero():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float(0) == 0.0


def test_ensure_float_with_infinity():
    from application.services.financial.financial_ratio_service import _ensure_float

    result = _ensure_float(float("inf"), default=-1)
    assert result == float("inf")


def test_ensure_float_with_neg_infinity():
    from application.services.financial.financial_ratio_service import _ensure_float

    result = _ensure_float(float("-inf"), default=-1)
    assert result == float("-inf")


def test_ensure_float_with_bool():
    from application.services.financial.financial_ratio_service import _ensure_float

    assert _ensure_float(True) == 1.0
    assert _ensure_float(False) == 0.0


def test_ensure_float_very_large():
    from application.services.financial.financial_ratio_service import _ensure_float

    large = 1e15
    assert _ensure_float(large) == 1e15


# -- handle_financial_ratio_query ----------------------------------------


def test_financial_ratio_empty_tickers_returns_error():
    from application.services.financial.financial_ratio_service import handle_financial_ratio_query

    result = handle_financial_ratio_query(tickers=[], field="pe")
    assert result == {"error": "Missing ticker"}


@patch("application.services.financial.financial_ratio_service.get_cache_manager")
@patch("application.services.financial.financial_ratio_service.VNStockClient")
def test_financial_ratio_single_ticker(mock_client, mock_cache):
    mock_cache.return_value = None
    mock_fin = MagicMock()
    mock_fin.financial_statement.return_value = MagicMock()
    mock_fin.financial_statement.return_value.empty = True
    mock_fin.market_data.return_value = {"current_price": 80000}
    mock_client.return_value.company = mock_fin
    mock_client.return_value.ticker = "VCB"

    from application.services.financial.financial_ratio_service import handle_financial_ratio_query

    result = handle_financial_ratio_query(tickers=["VCB"], field="pe")
    assert "VCB" in result
    assert "error" in result["VCB"]


# -- handle_ranking_query ------------------------------------------------


def test_ranking_single_ticker_returns_error():
    from application.services.financial.ranking_service import handle_ranking_query

    result = handle_ranking_query(tickers=["VNM"])
    assert "error" in result


@patch("application.services.financial.ranking_service.get_price_data")
def test_ranking_two_tickers(mock_get_price):
    def side_effect(ticker, *a, **kw):
        return {
            "ticker": ticker,
            "data": [
                {"date": "2026-01-03", "close": 100.0},
                {"date": "2026-01-04", "close": 102.0},
            ],
        }

    mock_get_price.side_effect = side_effect
    from application.services.financial.ranking_service import handle_ranking_query

    result = handle_ranking_query(tickers=["VCB", "VNM"], field="close")
    ranking = result["ranking"]
    assert "ranking_list" in ranking
    assert len(ranking["ranking_list"]) == 2
    assert ranking["field"] == "close"
    assert ranking["aggregate"] == "max"
    assert ranking["total_tickers"] == 2


@patch("application.services.financial.ranking_service.get_price_data")
def test_ranking_ticker_fetch_error(mock_get_price):
    def side_effect(ticker, *a, **kw):
        return {"error": f"No data for {ticker}"}

    mock_get_price.side_effect = side_effect
    from application.services.financial.ranking_service import handle_ranking_query

    result = handle_ranking_query(tickers=["VCB", "VNM"])
    ranking = result["ranking"]
    assert "error" in ranking
    assert ranking["error"] == "No valid data for ranking"


# -- perform_ranking (pure) -----------------------------------------------


def test_perform_ranking_basic():
    from application.services.financial.ranking_service import perform_ranking

    data = {
        "VCB": {"data": [{"close": 100}, {"close": 102}]},
        "VNM": {"data": [{"close": 80}, {"close": 85}]},
    }
    result = perform_ranking(data, "close", "max")
    assert "ranking_list" in result
    assert len(result["ranking_list"]) == 2
    assert result["ranking_list"][0]["ticker"] == "VCB"


def test_perform_ranking_with_errors():
    from application.services.financial.ranking_service import perform_ranking

    data = {
        "VCB": {"data": [{"close": 100}]},
        "INVALID": {"error": "No data"},
    }
    result = perform_ranking(data, "close", "max")
    assert "error" not in result
    assert len(result["ranking_list"]) == 1


def test_perform_ranking_all_errors():
    from application.services.financial.ranking_service import perform_ranking

    data = {"A": {"error": "x"}, "B": {"error": "y"}}
    result = perform_ranking(data, "close", "max")
    assert "error" in result


def test_perform_ranking_min_aggregate():
    from application.services.financial.ranking_service import perform_ranking

    data = {
        "VCB": {"data": [{"close": 100}, {"close": 102}]},
        "VNM": {"data": [{"close": 80}, {"close": 85}]},
    }
    result = perform_ranking(data, "close", "min")
    assert result["ranking_list"][0]["ticker"] == "VNM"


# -- perform_aggregation (pure) -------------------------------------------


def test_perform_aggregation_basic():
    from application.services.financial.aggregate_service import perform_aggregation

    data = {
        "VCB": {"data": [{"close": 100}, {"close": 102}]},
    }
    result = perform_aggregation(data, "close", "mean")
    assert "error" not in result
    assert result["result"]["value"] == 101.0


def test_perform_aggregation_nan_values():
    from application.services.financial.aggregate_service import perform_aggregation

    data = {
        "VCB": {"data": [{"close": 100}, {"close": float("nan")}, {"close": 102}]},
    }
    result = perform_aggregation(data, "close", "sum")
    assert result["result"]["value"] == 202.0
    assert result["result"]["function"] == "sum"


def test_perform_aggregation_no_valid_data():
    from application.services.financial.aggregate_service import perform_aggregation

    data = {"VCB": {"error": "No data"}}
    result = perform_aggregation(data, "close", "mean")
    assert "error" in result


def test_perform_aggregation_empty_data():
    from application.services.financial.aggregate_service import perform_aggregation

    result = perform_aggregation({}, "close", "mean")
    assert "error" in result


def test_perform_aggregation_all_nan():
    from application.services.financial.aggregate_service import perform_aggregation

    data = {"VCB": {"data": [{"close": float("nan")}, {"close": float("nan")}]}}
    result = perform_aggregation(data, "close", "mean")
    assert "error" in result
    assert "No valid data" in result["error"]


def test_perform_ranking_equal_values():
    from application.services.financial.ranking_service import perform_ranking

    data = {
        "VCB": {"data": [{"close": 100}]},
        "VNM": {"data": [{"close": 100}]},
    }
    result = perform_ranking(data, "close", "max")
    assert len(result["ranking_list"]) == 2


def test_perform_ranking_empty_data():
    from application.services.financial.ranking_service import perform_ranking

    result = perform_ranking({}, "close", "max")
    assert "error" in result


# -- interpretation helpers (pure) ----------------------------------------


def test_pe_interpretation():
    from application.services.financial.financial_ratio_service import get_pe_interpretation

    assert "undervalued" in get_pe_interpretation(5)
    assert "Moderate" in get_pe_interpretation(15)
    assert "overvalued" in get_pe_interpretation(25)
    assert "Significant" in get_pe_interpretation(50)


def test_roe_interpretation():
    from application.services.financial.financial_ratio_service import get_roe_interpretation

    assert "Poor" in get_roe_interpretation(2)
    assert "Good" in get_roe_interpretation(20)
    assert "Exceptional" in get_roe_interpretation(30)


def test_pb_interpretation():
    from application.services.financial.financial_ratio_service import get_pb_interpretation

    assert "undervalued" in get_pb_interpretation(0.5)
    assert "Moderate" in get_pb_interpretation(2)
    assert "overvalued" in get_pb_interpretation(5)
