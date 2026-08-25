"""Unit tests for VNStockClient with mocked vnstock dependency."""

from unittest.mock import patch
import pandas as pd
from infrastructure.api_clients.vn_stock_client import VNStockClient


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_client_init_default_ticker(mock_quote, mock_company):
    client = VNStockClient()
    assert client.ticker == "VCB"
    mock_company.assert_called_once_with(symbol="VCB", source="KBS")
    mock_quote.assert_called_once_with(symbol="VCB", source="VCI")


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_client_init_custom_ticker(mock_quote, mock_company):
    client = VNStockClient(ticker="VNM", source="VCI")
    assert client.ticker == "VNM"
    mock_company.assert_called_once_with(symbol="VNM", source="VCI")
    mock_quote.assert_called_once_with(symbol="VNM", source="VCI")


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_company_info(mock_quote, mock_company):
    mock_company.return_value.overview.return_value = pd.DataFrame(
        {"company_name": ["VCB"], "industry": ["Banking"]}
    )
    client = VNStockClient()
    result = client.company_info()
    assert not result.empty
    assert result["company_name"].iloc[0] == "VCB"


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_fetch_trading_data_returns_dataframe(mock_quote, mock_company):
    mock_quote.return_value.history.return_value = pd.DataFrame(
        {
            "time": ["2026-03-01", "2026-03-02"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000, 1100],
        }
    )
    client = VNStockClient()
    df = client.fetch_trading_data(start="2026-03-01", end="2026-03-02", interval="1d")
    assert not df.empty
    assert "date" in df.columns
    assert "close" in df.columns


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_fetch_trading_data_none_returns_empty(mock_quote, mock_company):
    mock_quote.return_value.history.return_value = pd.DataFrame()
    client = VNStockClient()
    df = client.fetch_trading_data(start="2026-01-01", end="2026-01-10", interval="1d")
    assert df.empty


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_fetch_trading_data_raises_on_none_start(mock_quote, mock_company):
    import pytest

    client = VNStockClient()
    with pytest.raises(ValueError, match="start and end must not be None"):
        client.fetch_trading_data(start=None, end=None)


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_fetch_trading_data_filters_by_date_range(mock_quote, mock_company):
    mock_quote.return_value.history.return_value = pd.DataFrame(
        {
            "time": ["2026-01-01", "2026-01-15", "2026-02-01"],
            "open": [100.0, 101.0, 102.0],
            "high": [102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0],
            "close": [101.0, 102.0, 103.0],
            "volume": [1000, 1100, 1200],
        }
    )
    client = VNStockClient()
    df = client.fetch_trading_data(start="2026-01-10", end="2026-01-20", interval="1d")
    for _, row in df.iterrows():
        assert "2026-01-10" <= row["date"] <= "2026-01-20"


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_fetch_trading_data_missing_close_column(mock_quote, mock_company):
    mock_quote.return_value.history.return_value = pd.DataFrame(
        {
            "time": ["2026-03-01", "2026-03-02"],
            "open": [100.0, 101.0],
        }
    )
    client = VNStockClient()
    df = client.fetch_trading_data(start="2026-03-01", end="2026-03-02", interval="1d")
    assert "close" not in df.columns or df["close"].isna().all()


@patch("infrastructure.api_clients.vn_stock_client.Company")
@patch("infrastructure.api_clients.vn_stock_client.Quote")
def test_fetch_trading_data_returns_empty_on_api_error(mock_quote, mock_company):
    mock_quote.return_value.history.side_effect = ValueError("404 - Not Found")
    client = VNStockClient()
    df = client.fetch_trading_data(start="2026-01-01", end="2026-01-10", interval="invalid")
    assert df.empty
