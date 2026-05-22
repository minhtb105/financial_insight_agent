"""Unit tests for market services — price, compare, indicator."""

from unittest.mock import patch, MagicMock

# -- handle_price_query ---------------------------------------------------


def test_price_empty_ticker_returns_error():
    from application.services.market.price_service import handle_price_query

    result = handle_price_query(tickers=[])
    assert "error" in result


@patch("shared.price_data.get_price_data")
def test_price_single_ticker(mock_get_price):
    mock_get_price.return_value = {
        "ticker": "VCB",
        "data": [
            {
                "date": "2026-01-03",
                "close": 101.0,
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "volume": 1000,
            },
        ],
    }
    from application.services.market.price_service import handle_price_query

    result = handle_price_query(tickers=["VCB"], field="close")
    assert "VCB" in result
    vcb = result["VCB"]
    assert vcb["ticker"] == "VCB"
    assert len(vcb["data"]) == 1
    assert vcb["data"][0]["close"] == 101.0


# -- handle_compare_query -------------------------------------------------


def test_compare_missing_tickers_returns_error():
    from application.services.market.compare_service import handle_compare_query

    result = handle_compare_query(tickers=[], compare_with=["VNM"], field="close")
    assert "error" in result


def test_compare_empty_ref_tickers_returns_error():
    from application.services.market.compare_service import handle_compare_query

    result = handle_compare_query(tickers=["VNM"], compare_with=[], field="close")
    assert "error" in result


@patch("application.services.market.compare_service.get_price_data")
def test_compare_two_tickers(mock_get_price):
    mock_get_price.return_value = {
        "ticker": "VCB",
        "data": [{"date": "2026-01-03", "close": 101.0}, {"date": "2026-01-04", "close": 102.0}],
    }
    from application.services.market.compare_service import handle_compare_query

    result = handle_compare_query(tickers=["VCB"], compare_with=["VNM"], field="close")
    assert "comparison" in result
    assert result["main_tickers"] == ["VCB"]
    assert result["compare_tickers"] == ["VNM"]
    assert result["requested_field"] == "close"


@patch("application.services.market.compare_service.get_price_data")
def test_compare_three_way(mock_get_price):
    mock_get_price.return_value = {
        "ticker": "VCB",
        "data": [{"date": "2026-01-03", "close": 100.0}],
    }
    from application.services.market.compare_service import handle_compare_query

    result = handle_compare_query(
        tickers=["VCB", "HPG", "VNM"], compare_with=["ACB"], field="close"
    )
    assert "comparison" in result
    assert len(result["main_tickers"]) == 3
    assert result["compare_tickers"] == ["ACB"]
    assert result["requested_field"] == "close"


# -- handle_indicator_query -----------------------------------------------


def test_indicator_empty_ticker_returns_error():
    from application.services.market.indicator_service import handle_indicator_query

    result = handle_indicator_query(tickers=[], indicator="sma")
    assert "error" in result


@patch("application.services.market.indicator_service.get_cache_manager")
@patch("application.services.market.indicator_service.VNStockClient")
def test_indicator_sma(mock_client, mock_cache):
    mock_cache.return_value = None
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = __import__("pandas").DataFrame(
        {"close": [float(d) for d in range(1, 15)]}
    )
    mock_client.return_value = mock_instance

    from application.services.market.indicator_service import handle_indicator_query

    result = handle_indicator_query(tickers=["VCB"], indicator="sma")
    assert "VCB" in result
    vcb = result["VCB"]
    assert "sma_20" in vcb


@patch("application.services.market.indicator_service.get_cache_manager")
@patch("application.services.market.indicator_service.VNStockClient")
def test_indicator_rsi(mock_client, mock_cache):
    import pandas as pd
    from datetime import datetime

    mock_cache.return_value = None
    mock_instance = MagicMock()
    dates = [datetime(2026, 1, d) for d in range(1, 20)]
    mock_instance.fetch_trading_data.return_value = pd.DataFrame(
        {"date": dates, "close": [float(d) for d in range(1, 20)]}
    )
    mock_client.return_value = mock_instance

    from application.services.market.indicator_service import handle_indicator_query

    result = handle_indicator_query(tickers=["VCB"], indicator="rsi")
    assert "VCB" in result
    vcb = result["VCB"]
    assert "rsi_14" in vcb
    assert len(vcb["rsi_14"]) > 0


@patch("application.services.market.indicator_service.get_cache_manager")
@patch("application.services.market.indicator_service.VNStockClient")
def test_indicator_insufficient_data(mock_client, mock_cache):
    mock_cache.return_value = None
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = __import__("pandas").DataFrame(
        {"close": [100.0]}
    )
    mock_client.return_value = mock_instance

    from application.services.market.indicator_service import handle_indicator_query

    result = handle_indicator_query(tickers=["VCB"], indicator="sma")
    assert "sma_20" in result["VCB"]
    assert result["VCB"]["sma_20"] == []


# -- handle_price_query with timeframe ------------------------------------


@patch("shared.price_data.get_price_data")
def test_price_with_invalid_field_fallback(mock_get_price):
    mock_get_price.return_value = {
        "ticker": "VCB",
        "data": [{"date": "2026-01-03", "close": 100.0}],
    }
    from application.services.market.price_service import handle_price_query

    result = handle_price_query(tickers=["VCB"], field="nonexistent")
    assert "VCB" in result
    assert result["VCB"]["ticker"] == "VCB"


@patch("shared.price_data.get_price_data")
def test_price_api_exception(mock_get_price):
    mock_get_price.side_effect = Exception("API down")
    from application.services.market.price_service import handle_price_query

    result = handle_price_query(tickers=["VCB"])
    assert "error" in result or "VCB" in result


@patch("shared.price_data.get_price_data")
def test_price_with_timeframe(mock_get_price):
    mock_get_price.return_value = {
        "ticker": "VCB",
        "data": [{"date": "2026-01-03", "close": 100.0}],
    }
    from application.services.market.price_service import handle_price_query

    result = handle_price_query(tickers=["VCB"], months=1)
    assert "VCB" in result
    assert result["VCB"]["ticker"] == "VCB"
    assert len(result["VCB"]["data"]) == 1
