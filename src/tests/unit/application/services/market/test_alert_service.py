"""Unit tests for alert_service — AlertService and helpers."""

from unittest.mock import patch, MagicMock
import pandas as pd

# -- module-level handle_alert_query --------------------------------------


def test_alert_empty_tickers_returns_error():
    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=[], threshold=100.0)
    assert "error" in result


def test_alert_none_threshold_returns_error():
    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB"], threshold=None)
    assert "error" in result


@patch("application.services.market.alert_service.VNStockClient")
def test_alert_above_threshold(mock_client):
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = pd.DataFrame(
        {
            "time": ["2026-03-08", "2026-03-09", "2026-03-10"],
            "close": [100.0, 101.0, 105.0],
            "open": [99.0, 100.0, 104.0],
            "high": [101.0, 102.0, 106.0],
            "low": [98.0, 99.0, 103.0],
            "volume": [1000, 1100, 1200],
        }
    )
    mock_client.return_value = mock_instance

    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB"], threshold=103.0, condition="above")
    alert = result["alerts"][0]
    assert alert["ticker"] == "VCB"
    assert alert["current_price"] == 105.0
    assert alert["threshold"] == 103.0
    assert alert["condition"] == "above"
    assert alert["triggered"] is True


@patch("application.services.market.alert_service.VNStockClient")
def test_alert_below_threshold_not_triggered(mock_client):
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = pd.DataFrame(
        {
            "time": ["2026-03-08", "2026-03-09", "2026-03-10"],
            "close": [100.0, 101.0, 105.0],
            "open": [99.0, 100.0, 104.0],
            "high": [101.0, 102.0, 106.0],
            "low": [98.0, 99.0, 103.0],
            "volume": [1000, 1100, 1200],
        }
    )
    mock_client.return_value = mock_instance

    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB"], threshold=103.0, condition="below")
    alert = result["alerts"][0]
    assert alert["ticker"] == "VCB"
    assert alert["current_price"] == 105.0
    assert alert["threshold"] == 103.0
    assert alert["condition"] == "below"
    assert alert["triggered"] is False


# -- AlertService._check_single ------------------------------------------


def make_mock_service():
    from application.services.market.alert_service import AlertService

    svc = AlertService.__new__(AlertService)
    svc.logger = MagicMock()
    return svc


def test_check_single_no_data():
    svc = make_mock_service()
    client = MagicMock()
    client.fetch_trading_data.return_value = pd.DataFrame()
    with patch("application.services.market.alert_service.VNStockClient", return_value=client):
        result = svc._check_single("VCB", 100.0, "above")
    assert "error" in result


def test_check_single_missing_close():
    svc = make_mock_service()
    client = MagicMock()
    client.fetch_trading_data.return_value = pd.DataFrame(
        {
            "time": ["2026-03-08", "2026-03-09"],
            "open": [100.0, 101.0],
        }
    )
    with patch("application.services.market.alert_service.VNStockClient", return_value=client):
        result = svc._check_single("VCB", 100.0, "above")
    assert "error" in result


def test_check_single_price_equals_threshold():
    svc = make_mock_service()
    client = MagicMock()
    client.fetch_trading_data.return_value = pd.DataFrame(
        {
            "time": ["2026-03-08", "2026-03-09", "2026-03-10"],
            "close": [99.0, 100.0, 100.0],
            "open": [98.0, 99.0, 99.0],
            "high": [100.0, 101.0, 101.0],
            "low": [97.0, 98.0, 98.0],
            "volume": [1000, 1100, 1200],
        }
    )
    with patch("application.services.market.alert_service.VNStockClient", return_value=client):
        result = svc._check_single("VCB", 100.0, "above")
    assert result["triggered"] is True
    assert result["current_price"] == 100.0
    assert result["threshold"] == 100.0
    assert result["condition"] == "above"


# -- handle_query summary -------------------------------------------------


@patch("application.services.market.alert_service.VNStockClient")
def test_alert_summary(mock_client):
    mock_instance = MagicMock()
    mock_instance.fetch_trading_data.return_value = pd.DataFrame(
        {
            "time": ["2026-03-08", "2026-03-09", "2026-03-10"],
            "close": [90.0, 95.0, 105.0],
            "open": [89.0, 94.0, 104.0],
            "high": [91.0, 96.0, 106.0],
            "low": [88.0, 93.0, 103.0],
            "volume": [1000, 1100, 1200],
        }
    )
    mock_client.return_value = mock_instance

    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB", "HPG"], threshold=100.0, condition="above")
    assert "alerts" in result
    assert "summary" in result
    assert result["summary"]["total"] == 2
    assert result["summary"]["triggered"] == 2
    assert result["summary"]["total"] == 2
    assert result["timeframe"] == "1d"


# -- edge cases -----------------------------------------------------------


@patch("application.services.market.alert_service.VNStockClient")
def test_alert_zero_threshold(mock_client):
    mock_client.return_value.fetch_trading_data.return_value = pd.DataFrame(
        {
            "time": ["2026-03-10"],
            "close": [105.0],
            "open": [104.0],
            "high": [106.0],
            "low": [103.0],
            "volume": [1000],
        }
    )
    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB"], threshold=0.0)
    assert "alerts" in result
    assert result["alerts"][0]["triggered"] is True


@patch("application.services.market.alert_service.VNStockClient")
def test_alert_negative_threshold(mock_client):
    mock_client.return_value.fetch_trading_data.return_value = pd.DataFrame(
        {
            "time": ["2026-03-10"],
            "close": [105.0],
            "open": [104.0],
            "high": [106.0],
            "low": [103.0],
            "volume": [1000],
        }
    )
    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB"], threshold=-50.0)
    assert "alerts" in result
    assert result["alerts"][0]["triggered"] is True


@patch("application.services.market.alert_service.VNStockClient")
def test_alert_empty_data_closes(mock_client):
    mock_client.return_value.fetch_trading_data.return_value = pd.DataFrame()
    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB"], threshold=100.0)
    assert "alerts" in result
    assert result["alerts"][0]["error"] == "No price data available"


@patch("application.services.market.alert_service.VNStockClient")
def test_alert_single_point(mock_client):
    mock_client.return_value.fetch_trading_data.return_value = pd.DataFrame(
        {"time": ["2026-03-10"], "close": [105.0]}
    )
    from application.services.market.alert_service import handle_alert_query

    result = handle_alert_query(tickers=["VCB"], threshold=100.0, condition="above")
    assert "alerts" in result
    assert len(result["alerts"]) == 1
