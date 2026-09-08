"""Tests for shared.price_data shim — delegates to MarketDataPort via registry."""

from unittest.mock import MagicMock

from shared.service_registry import set_service, clear
from shared.ports.market_data_port import MarketDataPort
from shared.ports.cache_port import CachePort


class FakeMarketData(MarketDataPort):
    def get_price_data(self, ticker, start_date, end_date, interval="1d"):
        return {"ticker": ticker, "data": [{"date": "2026-01-03", "close": 101.0}], "start_date": start_date, "end_date": end_date}


class FakeCache(CachePort):
    def get(self, key): return None
    def set(self, key, value, ttl_hours=1.0): pass
    def delete(self, key): pass


def test_shim_delegates_to_market_data():
    from shared.price_data import get_price_data
    # Setup fake service
    from application.services.market.price_service import PriceService
    svc = PriceService(cache=FakeCache(), market_data=FakeMarketData())
    set_service("price", svc)
    result = get_price_data(ticker="VCB", start_date="2026-01-01", end_date="2026-01-03")
    assert result["ticker"] == "VCB"
    assert len(result["data"]) == 1
    clear()


def test_shim_without_service_returns_error():
    from shared.price_data import get_price_data
    clear()
    result = get_price_data(ticker="VCB", start_date="2026-01-01", end_date="2026-01-03")
    assert "error" in result
