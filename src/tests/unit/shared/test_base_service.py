"""Unit tests for BaseService — parallel fetch, time params, NaN checks, cache, validation."""

from unittest.mock import patch, MagicMock

from shared.base_service import BaseService


def test_empty_tickers_returns_error():
    service = BaseService("test")
    result = service.for_each_ticker([], lambda t: {"data": t})
    assert "error" in result
    assert result["error"] == "Missing ticker"


def test_single_ticker():
    service = BaseService("test")
    result = service.for_each_ticker(["VCB"], lambda t: {"data": t})
    assert result["VCB"]["data"] == "VCB"


def test_multiple_tickers():
    service = BaseService("test")
    result = service.for_each_ticker(["VCB", "HPG"], lambda t: {"data": t})
    assert result["VCB"]["data"] == "VCB"
    assert result["HPG"]["data"] == "HPG"


def test_ticker_exception_isolated():
    def fetch(t):
        if t == "BAD":
            raise ValueError("invalid")
        return {"data": t}

    service = BaseService("test")
    result = service.for_each_ticker(["VCB", "BAD", "HPG"], fetch)
    assert result["VCB"]["data"] == "VCB"
    assert "error" in result["BAD"]
    assert result["HPG"]["data"] == "HPG"


def test_all_tickers_fail():
    def fetch(t):
        raise RuntimeError("down")

    service = BaseService("test")
    result = service.for_each_ticker(["VCB", "HPG"], fetch)
    assert "error" in result["VCB"]
    assert "error" in result["HPG"]


def test_max_workers_clamped():
    service = BaseService("test")
    result = service.for_each_ticker(
        ["VCB"], lambda t: {"data": t}, max_workers=100
    )
    assert result["VCB"]["data"] == "VCB"


def test_build_time_params_days():
    service = BaseService("test")
    start, end = service._build_time_params(days=7)
    assert start is not None
    assert end is not None


def test_build_time_params_exact():
    service = BaseService("test")
    start, end = service._build_time_params(start_date="2026-01-01", end_date="2026-01-31")
    assert start == "2026-01-01"
    assert end == "2026-01-31"


def test_build_time_params_empty():
    service = BaseService("test")
    start, end = service._build_time_params()
    assert start is not None
    assert end is not None


def test_is_nan_none():
    assert BaseService._is_nan(None) is True


def test_is_nan_nan():
    import math
    assert BaseService._is_nan(float("nan")) is True


def test_is_nan_valid_number():
    assert BaseService._is_nan(100.0) is False


def test_is_nan_string():
    assert BaseService._is_nan("abc") is True


def test_is_nan_zero():
    assert BaseService._is_nan(0) is False


def test_require_tickers_empty():
    service = BaseService("test")
    result = service._require_tickers([])
    assert result is not None
    assert "error" in result


def test_require_tickers_valid():
    service = BaseService("test")
    assert service._require_tickers(["VCB"]) is None


def test_require_tickers_min_count():
    service = BaseService("test")
    result = service._require_tickers(["VCB"], min_count=2)
    assert result is not None
    assert "Need at least 2" in result["error"]


@patch("shared.base_service.get_cache_manager")
def test_get_cache_manager_returns_none_on_error(mock_get):
    mock_get.side_effect = RuntimeError("no cache")
    service = BaseService("test")
    assert service._get_cache_manager() is None


@patch("shared.base_service.get_cache_manager")
def test_cached_fetch_cache_hit(mock_get):
    mock_cache = MagicMock()
    mock_cache.get.return_value = {"cached": "data"}
    mock_get.return_value = mock_cache
    service = BaseService("test")
    result = service._cached_fetch("price", "VCB", lambda: {"fresh": "data"})
    assert result == {"cached": "data"}


@patch("shared.base_service.get_cache_manager")
def test_cached_fetch_cache_miss(mock_get):
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_get.return_value = mock_cache
    service = BaseService("test")
    result = service._cached_fetch("price", "VCB", lambda: {"fresh": "data"})
    assert result == {"fresh": "data"}
    mock_cache.set.assert_called_once()


@patch("shared.base_service.get_cache_manager")
def test_cached_fetch_skips_set_on_error(mock_get):
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_get.return_value = mock_cache
    service = BaseService("test")
    result = service._cached_fetch("price", "VCB", lambda: {"error": "fail"})
    assert result == {"error": "fail"}
    mock_cache.set.assert_not_called()


@patch("shared.base_service.get_cache_manager")
def test_cached_fetch_no_cache_fallback(mock_get):
    mock_get.return_value = None
    service = BaseService("test")
    result = service._cached_fetch("price", "VCB", lambda: {"fresh": "data"})
    assert result == {"fresh": "data"}
