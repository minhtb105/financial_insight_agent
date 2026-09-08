"""Unit tests for financial services — strict DI."""

import pandas as pd
from shared.service_registry import set_service, clear
from shared.ports.cache_port import CachePort
from shared.ports.financial_port import FinancialPort
from shared.ports.market_data_port import MarketDataPort

class FakeCache(CachePort):
    def get(self, key): return None
    def set(self, key, value, ttl_hours=1.0): pass
    def delete(self, key): pass

class FakeFinancialPort(FinancialPort):
    def get_financial_statement(self, ticker):
        return pd.DataFrame({"eps": [1.0], "equity": [100.0], "net_profit": [10.0], "book_value_per_share": [10.0], "shares_outstanding": [10.0], "current_assets": [50.0], "current_liabilities": [25.0], "total_liabilities": [50.0], "revenue": [100.0], "total_assets": [200.0], "cash_and_equivalents": [20.0], "marketable_securities": [10.0], "dividend_per_share": [0.5]})
    def get_market_data(self, ticker):
        return {"current_price": 10.0}

class FakeMarketData(MarketDataPort):
    def get_price_data(self, ticker, start_date, end_date, interval="1d"):
        return {"ticker": ticker, "data": [{"date": "2026-01-03", "close": 101.0, "open": 100.0, "high": 102.0, "low": 99.0, "volume": 1000}], "start_date": start_date, "end_date": end_date}

def test_financial_ratio_empty_tickers_returns_error():
    from application.services.financial.financial_ratio_service import FinancialRatioService
    svc = FinancialRatioService(cache=FakeCache(), financial_port=FakeFinancialPort())
    set_service("financial_ratio", svc)
    from application.services.financial.financial_ratio_service import handle_financial_ratio_query
    result = handle_financial_ratio_query(tickers=[])
    assert "error" in result
    clear()

def test_financial_ratio_single_ticker():
    from application.services.financial.financial_ratio_service import FinancialRatioService
    svc = FinancialRatioService(cache=FakeCache(), financial_port=FakeFinancialPort())
    set_service("financial_ratio", svc)
    from application.services.financial.financial_ratio_service import handle_financial_ratio_query
    result = handle_financial_ratio_query(tickers=["VCB"], field="pe")
    assert "VCB" in result
    clear()

def test_ranking_single_ticker_returns_error():
    from application.services.financial.ranking_service import RankingService
    svc = RankingService(cache=FakeCache(), market_data=FakeMarketData())
    set_service("ranking", svc)
    from application.services.financial.ranking_service import handle_ranking_query
    result = handle_ranking_query(tickers=["VCB"])
    assert "error" in result
    clear()

def test_ranking_two_tickers():
    from application.services.financial.ranking_service import RankingService
    svc = RankingService(cache=FakeCache(), market_data=FakeMarketData())
    set_service("ranking", svc)
    from application.services.financial.ranking_service import handle_ranking_query
    result = handle_ranking_query(tickers=["VCB", "VNM"], field="close")
    assert "ranking" in result
    clear()

def test_ranking_ticker_fetch_error():
    from application.services.financial.ranking_service import RankingService
    class ErrMarketData(MarketDataPort):
        def get_price_data(self, ticker, start_date, end_date, interval="1d"):
            return {"error": "No data"}
    svc = RankingService(cache=FakeCache(), market_data=ErrMarketData())
    set_service("ranking", svc)
    from application.services.financial.ranking_service import handle_ranking_query
    result = handle_ranking_query(tickers=["VCB", "VNM"])
    assert "ranking" in result or "error" in result
    clear()
