"""Simplified portfolio tests — strict DI via Fake ports."""

from shared.service_registry import set_service, clear
from shared.ports.cache_port import CachePort
from shared.ports.news_port import NewsPort
from shared.ports.market_data_port import MarketDataPort
from shared.ports.company_port import CompanyPort

class FakeCache(CachePort):
    def get(self, key): return None
    def set(self, key, value, ttl_hours=1.0): pass
    def delete(self, key): pass

class FakeNewsPort(NewsPort):
    def fetch_news(self, ticker):
        return [{"title": "VCB kinh doanh kỷ lục", "content": "Lợi nhuận tăng mạnh", "source": "VnEconomy", "url": "https://example.com", "date": "2026-03-01", "ticker": ticker}]

class FakeMarketData(MarketDataPort):
    def get_price_data(self, ticker, start_date, end_date, interval="1d"):
        return {"ticker": ticker, "data": [{"date": "2026-03-01", "close": 100.0, "open": 99.0, "high": 101.0, "low": 98.0, "volume": 1000}], "start_date": start_date, "end_date": end_date}

class FakeCompanyPort(CompanyPort):
    def get_overview(self, ticker): 
        import pandas as pd
        return pd.DataFrame({"sector": ["Banking"], "ticker": [ticker]})
    def list_companies(self):
        import pandas as pd
        return pd.DataFrame({"sector": ["Banking"], "ticker": ["VCB"]})

def test_news_sentiment_empty_tickers_returns_error():
    from application.services.portfolio.news_sentiment_service import NewsSentimentService
    svc = NewsSentimentService(cache=FakeCache(), news_port=FakeNewsPort())
    set_service("news", svc)
    from application.services.portfolio.news_sentiment_service import handle_news_sentiment_query
    result = handle_news_sentiment_query(tickers=[], field="news")
    assert "error" in result
    clear()

def test_news_sentiment_valid_ticker():
    from application.services.portfolio.news_sentiment_service import NewsSentimentService
    svc = NewsSentimentService(cache=FakeCache(), news_port=FakeNewsPort())
    set_service("news", svc)
    from application.services.portfolio.news_sentiment_service import handle_news_sentiment_query
    result = handle_news_sentiment_query(tickers=["VCB"], field="news")
    assert "news" in result
    assert len(result["news"]["VCB"]) == 1
    assert result["news"]["VCB"][0]["title"] == "VCB kinh doanh kỷ lục"
    clear()
