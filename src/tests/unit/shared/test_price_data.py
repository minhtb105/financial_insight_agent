"""Unit tests for shared price_data module."""

from unittest.mock import patch, MagicMock

import pandas as pd

from shared.price_data import get_price_data


def test_get_price_data_missing_params():
    result = get_price_data(ticker="VCB")
    assert "error" in result


@patch("shared.price_data.VNStockClient")
@patch("shared.price_data.get_cache_manager")
def test_get_price_data_with_days(mock_cache, mock_client):
    mock_cache.return_value = None
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = pd.DataFrame(
        {
            "date": ["2026-03-08", "2026-03-09", "2026-03-10"],
            "open": [100.0, 101.0, 102.0],
            "high": [102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0],
            "close": [101.0, 102.0, 103.0],
            "volume": [1000, 1100, 1200],
        }
    )
    mock_client.return_value = mock_instance

    result = get_price_data(ticker="VCB", days=7, end_date="2026-03-10")
    assert "error" not in result
    assert result["ticker"] == "VCB"
    assert len(result["data"]) == 3
    assert result["data"][0]["close"] == 101.0
    assert result["data"][0]["open"] == 100.0
    assert result["data"][1]["high"] == 103.0
    assert result["data"][2]["volume"] == 1200
    mock_client.assert_called_once_with(ticker="VCB")
    mock_instance.fetch_trading_data.assert_called_once()


# -- edge cases -------------------------------------------------------------


@patch("shared.price_data.VNStockClient")
@patch("shared.price_data.get_cache_manager")
def test_get_price_data_nan_close(mock_cache, mock_client):
    mock_cache.return_value = None
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = pd.DataFrame(
        {
            "date": ["2026-03-08"],
            "close": [float("nan")],
            "open": [100.0],
            "high": [102.0],
            "low": [99.0],
            "volume": [1000],
        }
    )
    mock_client.return_value = mock_instance
    import math
    result = get_price_data(ticker="VCB", days=7)
    mock_client.assert_called_once_with(ticker="VCB")
    assert "error" not in result
    assert result["ticker"] == "VCB"
    assert len(result["data"]) == 1
    assert math.isnan(result["data"][0]["close"])


@patch("shared.price_data.VNStockClient")
@patch("shared.price_data.get_cache_manager")
def test_get_price_data_client_raises(mock_cache, mock_client):
    mock_cache.return_value = None
    mock_client.return_value.fetch_trading_data.side_effect = ValueError("API error")
    result = get_price_data(ticker="VCB", days=7)
    assert "error" in result
    mock_client.assert_called_once_with(ticker="VCB")


@patch("shared.price_data.VNStockClient")
@patch("shared.price_data.get_cache_manager")
def test_get_price_data_cache_hit(mock_cache, mock_client):
    mock_cache.return_value.get.return_value = [{"close": 100.0}]
    mock_cache.return_value.ttl_hours = 1
    result = get_price_data(ticker="VCB", days=7)
    assert result == [{"close": 100.0}]
    mock_client.return_value.fetch_trading_data.assert_not_called()


@patch("shared.price_data.VNStockClient")
@patch("shared.price_data.get_cache_manager")
def test_get_price_data_empty_dataframe(mock_cache, mock_client):
    mock_cache.return_value = None
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = pd.DataFrame()
    mock_client.return_value = mock_instance
    result = get_price_data(ticker="VCB", days=7)
    assert "error" in result
    assert "No data" in result["error"]


@patch("shared.price_data.VNStockClient")
@patch("shared.price_data.get_cache_manager")
def test_get_price_data_invalid_date(mock_cache, mock_client):
    result = get_price_data(ticker="VCB", start_date="not-a-date", end_date="2026-03-10")
    assert "error" in result


@patch("shared.price_data.VNStockClient")
@patch("shared.price_data.get_cache_manager")
def test_get_price_data_negative_days(mock_cache, mock_client):
    result = get_price_data(ticker="VCB", days=-1)
    assert "error" in result
