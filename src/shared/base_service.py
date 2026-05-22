import math
from typing import Any, TypeVar
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from infrastructure.observability import get_logger
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key
from shared.utils.time_processor import TimeProcessor

_FetchResult = TypeVar("_FetchResult")

_DEFAULT_MAX_WORKERS = 5
_MAX_WORKERS_CEILING = 16
_TIMEOUT_SECONDS = 30


class BaseService:
    def __init__(self, logger_name: str) -> None:
        self.logger = get_logger(logger_name)

    def for_each_ticker(
        self,
        tickers: list[str],
        fetch_fn: Callable[[str], dict[str, Any]],
        max_workers: int = _DEFAULT_MAX_WORKERS,
    ) -> dict[str, Any]:
        """Fetch data for multiple tickers in parallel with isolated error handling.

        Each ticker runs in its own thread. A single failure never blocks others.
        Note: creates a fresh executor per call; reuse via caller-level pool if hot path.
        """
        if not tickers:
            return {"error": "Missing ticker"}

        workers = max(1, min(max_workers, _MAX_WORKERS_CEILING))
        results: dict[str, Any] = {}

        overall_timeout = min(len(tickers) * _TIMEOUT_SECONDS, _TIMEOUT_SECONDS * 4)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(fetch_fn, t): t for t in tickers}
            try:
                for future in as_completed(futures, timeout=overall_timeout):
                    ticker = futures[future]
                    try:
                        results[ticker] = future.result(timeout=_TIMEOUT_SECONDS)
                    except TimeoutError:
                        self.logger.error(f"Timeout for {ticker} after {_TIMEOUT_SECONDS}s")
                        results[ticker] = {"error": f"Timeout fetching {ticker}"}
                    except Exception as e:
                        self.logger.error(f"Failed for {ticker}: {e}")
                        results[ticker] = {"error": str(e)}
            except TimeoutError:
                self.logger.error("Overall timeout waiting for ticker futures")
                executor.shutdown(wait=False, cancel_futures=True)

        return results

    def _build_time_params(
        self,
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[str, str]:
        """Extract and process time parameters.
        
        Consolidates duplicate time-param-building logic from 4 services.
        Returns tuple of (start_date, end_date) as processed by TimeProcessor.
        """
        time_processor = TimeProcessor()
        time_query: dict[str, Any] = {}
        if days is not None:
            time_query["days"] = days
        if weeks is not None:
            time_query["weeks"] = weeks
        if months is not None:
            time_query["months"] = months
        if start_date is not None:
            time_query["start"] = start_date
        if end_date is not None:
            time_query["end"] = end_date
        time_params = time_processor.process_time_params(time_query)
        return time_params["start_date"], time_params["end_date"]

    @staticmethod
    def _is_nan(v: Any) -> bool:
        if v is None:
            return True
        try:
            return math.isnan(float(v))
        except (TypeError, ValueError):
            return True

    def _require_tickers(self, tickers: list[str], min_count: int = 1) -> dict[str, Any] | None:
        """Validate tickers list. Returns error dict or None if valid."""
        if not tickers or len(tickers) < min_count:
            msg = f"Need at least {min_count} ticker(s)" if min_count > 1 else "Missing ticker"
            self.logger.error(msg)
            return {"error": msg}
        return None

    def _fetch_single(self, ticker: str, start_date: str, end_date: str) -> dict[str, Any]:
        """Fetch price data for a single ticker. Shared across 3 services."""
        from shared.price_data import get_price_data
        try:
            data = get_price_data(ticker, start_date, end_date)
            if data and "error" not in data:
                return data
            self.logger.warning(f"No data for {ticker}")
            return {"error": f"No data for {ticker}"}
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {ticker}: {e}")
            return {"error": str(e)}

    def _cached_fetch(
        self,
        namespace: str,
        ticker: str,
        fetch_fn: Callable[[], _FetchResult],
        ttl_hours: int = 24,
        **extra_key_parts: Any,
    ) -> _FetchResult:
        """Cache-check → fetch → cache-set wrapper.
        
        Handles the common cache-then-fetch pattern used across all services.
        If no cache manager is available, falls through to fetch_fn directly.
        """
        cache = self._get_cache_manager()
        cache_key = make_cache_key(namespace, ticker, **extra_key_parts)
        if cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        result = fetch_fn()
        if cache and isinstance(result, dict) and "error" not in result:
            cache.set(cache_key, result, ttl_hours=ttl_hours)
        return result

    def _get_cache_manager(self) -> Any | None:
        """Get cache manager, returning None on any error.
        
        Consolidates identical 5-line _cache() methods from PriceService,
        PortfolioService, FinancialRatioService, SectorService, NewsSentimentService.
        """
        try:
            return get_cache_manager()
        except Exception:
            return None
