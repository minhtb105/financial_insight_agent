"""Unit tests for market services — price, compare, indicator (strict DI)."""

from unittest.mock import MagicMock

import pandas as pd
from shared.service_registry import set_service, clear
from shared.ports.market_data_port import MarketDataPort
from shared.ports.cache_port import CachePort


class FakeCache(CachePort):
    def get(self, key): return None
    def set(self, key, value, ttl_hours=1.0): pass
    def delete(self, key): pass


class FakeMarketData(MarketDataPort):
    def __init__(self, data):
        self._data = data
    def get_price_data(self, ticker, start_date, end_date, interval="1d"):
        # Return dict with data
        return {"ticker": ticker, "data": self._data, "start_date": start_date, "end_date": end_date}


def _setup_price_service(data):
    from application.services.market.price_service import PriceService
    svc = PriceService(cache=FakeCache(), market_data=FakeMarketData(data))
    set_service("price", svc)
    return svc


def _setup_compare_service(data):
    from application.services.market.compare_service import CompareService
    svc = CompareService(cache=FakeCache(), market_data=FakeMarketData(data))
    set_service("compare", svc)
    return svc


def _setup_indicator_service(df):
    from application.services.market.indicator_service import IndicatorService
    # Indicator needs DataFrame via market_data returning DataFrame-like dict, but it expects DataFrame from market_data.get_price_data?
    # Our MarketDataPort returns dict, but indicator currently expects DataFrame via market_data.get_price_data returning dict then converts to DataFrame
    # For test, we mock market_data to return DataFrame directly via side effect
    mock_md = MagicMock(spec=MarketDataPort)
    # Indicator's _fetch_single will call market_data.get_price_data and then convert to DataFrame internally
    # Let's make it return DataFrame-like dict that indicator can handle
    # Actually indicator's code does: result = self._market_data.get_price_data(...); data = pd.DataFrame(result["data"])
    # So we can make FakeMarketData return dict with data
    mock_md.get_price_data.return_value = {"ticker": "VCB", "data": [{"date": "2026-01-03", "close": 101.0}] * 20, "start_date": "2026-01-01", "end_date": "2026-01-20"}
    # But for simplicity, we will directly set service with mock
    svc = IndicatorService(cache=FakeCache(), market_data=mock_md)
    set_service("indicator", svc)
    return svc, mock_md


# -- handle_price_query ---------------------------------------------------

def test_price_empty_ticker_returns_error():
    _setup_price_service([{"date": "2026-01-03", "close": 101.0}])
    from application.services.market.price_service import handle_price_query
    result = handle_price_query(tickers=[])
    assert "error" in result
    clear()


def test_price_single_ticker():
    _setup_price_service([{"date": "2026-01-03", "close": 101.0, "open": 100.0, "high": 102.0, "low": 99.0, "volume": 1000}])
    from application.services.market.price_service import handle_price_query
    result = handle_price_query(tickers=["VCB"], field="close")
    assert "VCB" in result
    vcb = result["VCB"]
    assert vcb["ticker"] == "VCB"
    assert len(vcb["data"]) == 1
    assert vcb["data"][0]["close"] == 101.0
    clear()


# -- handle_compare_query -------------------------------------------------

def test_compare_missing_tickers_returns_error():
    _setup_compare_service([{"date": "2026-01-03", "close": 101.0}])
    from application.services.market.compare_service import handle_compare_query
    result = handle_compare_query(tickers=[], compare_with=["VNM"], field="close")
    assert "error" in result
    clear()


def test_compare_empty_ref_tickers_returns_error():
    _setup_compare_service([{"date": "2026-01-03", "close": 101.0}])
    from application.services.market.compare_service import handle_compare_query
    result = handle_compare_query(tickers=["VNM"], compare_with=[], field="close")
    assert "error" in result
    clear()


def test_compare_two_tickers():
    _setup_compare_service([{"date": "2026-01-03", "close": 101.0}, {"date": "2026-01-04", "close": 102.0}])
    from application.services.market.compare_service import handle_compare_query
    result = handle_compare_query(tickers=["VCB"], compare_with=["VNM"], field="close")
    assert "comparison" in result
    assert result["main_tickers"] == ["VCB"]
    assert result["compare_tickers"] == ["VNM"]
    assert result["requested_field"] == "close"
    clear()


def test_compare_three_way():
    _setup_compare_service([{"date": "2026-01-03", "close": 100.0}])
    from application.services.market.compare_service import handle_compare_query
    result = handle_compare_query(tickers=["VCB", "HPG", "VNM"], compare_with=["ACB"], field="close")
    assert "comparison" in result
    assert len(result["main_tickers"]) == 3
    assert result["compare_tickers"] == ["ACB"]
    assert result["requested_field"] == "close"
    clear()


# -- handle_indicator_query -----------------------------------------------

def test_indicator_empty_ticker_returns_error():
    svc, _ = _setup_indicator_service(pd.DataFrame({"close": [1]*20}))
    from application.services.market.indicator_service import handle_indicator_query
    result = handle_indicator_query(tickers=[], indicator="sma")
    assert "error" in result
    clear()


def test_indicator_sma():
    from application.services.market.indicator_service import IndicatorService
    mock_md = MagicMock(spec=MarketDataPort)
    mock_md.get_price_data.return_value = {"ticker": "VCB", "data": [{"date": f"2026-01-{i:02d}", "close": float(i)} for i in range(1, 15)], "start_date": "2026-01-01", "end_date": "2026-01-14"}
    svc = IndicatorService(cache=FakeCache(), market_data=mock_md)
    set_service("indicator", svc)
    from application.services.market.indicator_service import handle_indicator_query
    result = handle_indicator_query(tickers=["VCB"], indicator="sma")
    assert "VCB" in result
    vcb = result["VCB"]
    assert "sma_20" in vcb or "sma" in str(vcb).lower()
    clear()


def test_indicator_rsi():
    from application.services.market.indicator_service import IndicatorService
    import pandas as pd
    from datetime import datetime
    mock_md = MagicMock(spec=MarketDataPort)
    dates = [datetime(2026, 1, d) for d in range(1, 20)]
    mock_md.get_price_data.return_value = {"ticker": "VCB", "data": [{"date": d.strftime("%Y-%m-%d"), "close": float(i)} for i, d in enumerate(dates, 1)], "start_date": "2026-01-01", "end_date": "2026-01-19"}
    svc = IndicatorService(cache=FakeCache(), market_data=mock_md)
    set_service("indicator", svc)
    from application.services.market.indicator_service import handle_indicator_query
    result = handle_indicator_query(tickers=["VCB"], indicator="rsi")
    assert "VCB" in result
    vcb = result["VCB"]
    assert "rsi_14" in vcb
    assert len(vcb["rsi_14"]) > 0
    clear()


def test_indicator_insufficient_data():
    from application.services.market.indicator_service import IndicatorService
    mock_md = MagicMock(spec=MarketDataPort)
    mock_md.get_price_data.return_value = {"ticker": "VCB", "data": [{"date": "2026-01-01", "close": 100.0}], "start_date": "2026-01-01", "end_date": "2026-01-01"}
    svc = IndicatorService(cache=FakeCache(), market_data=mock_md)
    set_service("indicator", svc)
    from application.services.market.indicator_service import handle_indicator_query
    result = handle_indicator_query(tickers=["VCB"], indicator="sma")
    assert "sma_20" in result["VCB"]
    assert result["VCB"]["sma_20"] == []
    clear()


# -- handle_price_query with timeframe ------------------------------------

def test_price_with_invalid_field_fallback():
    _setup_price_service([{"date": "2026-01-03", "close": 100.0}])
    from application.services.market.price_service import handle_price_query
    result = handle_price_query(tickers=["VCB"], field="nonexistent")
    assert "VCB" in result
    assert result["VCB"]["ticker"] == "VCB"
    clear()


def test_price_api_exception():
    from application.services.market.price_service import PriceService
    mock_md = MagicMock(spec=MarketDataPort)
    mock_md.get_price_data.side_effect = Exception("API down")
    svc = PriceService(cache=FakeCache(), market_data=mock_md)
    set_service("price", svc)
    from application.services.market.price_service import handle_price_query
    result = handle_price_query(tickers=["VCB"])
    assert "error" in result or "VCB" in result
    clear()


def test_price_with_timeframe():
    _setup_price_service([{"date": "2026-01-03", "close": 100.0}])
    from application.services.market.price_service import handle_price_query
    result = handle_price_query(tickers=["VCB"], months=1)
    assert "VCB" in result
    assert result["VCB"]["ticker"] == "VCB"
    assert len(result["VCB"]["data"]) == 1
    clear()
