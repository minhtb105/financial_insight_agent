import pytest
from unittest.mock import MagicMock
import pandas as pd


@pytest.fixture
def mock_redis_client():
    client = MagicMock()
    client.ping.return_value = True
    client.keys.return_value = []
    return client


@pytest.fixture
def mock_redis_cache(mock_redis_client, monkeypatch):
    monkeypatch.setattr(
        "infrastructure.cache.redis_cache.redis.Redis", lambda **kw: mock_redis_client
    )
    from infrastructure.cache.redis_cache import RedisCache

    cache = RedisCache(host="localhost", port=6379)
    return cache


@pytest.fixture
def sample_price_df():
    return pd.DataFrame(
        {
            "time": ["2026-01-03", "2026-01-04", "2026-01-05", "2026-01-06", "2026-01-07"],
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [102.0, 103.0, 104.0, 105.0, 106.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0],
            "volume": [1000, 1100, 1200, 1300, 1400],
        }
    )


@pytest.fixture
def sample_price_list():
    return [
        {
            "date": "2026-01-03",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000,
        },
        {
            "date": "2026-01-04",
            "open": 101.0,
            "high": 103.0,
            "low": 100.0,
            "close": 102.0,
            "volume": 1100,
        },
        {
            "date": "2026-01-05",
            "open": 102.0,
            "high": 104.0,
            "low": 101.0,
            "close": 103.0,
            "volume": 1200,
        },
    ]


@pytest.fixture
def sample_company_overview_df():
    return pd.DataFrame(
        {
            "ticker": ["VCB", "VNM"],
            "sector": ["banking", "food"],
            "company_name": ["Vietcombank", "Vinamilk"],
        }
    )


@pytest.fixture
def sample_empty_df():
    return pd.DataFrame()
