import logging
import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from concurrent.futures import as_completed
from typing import Any, TypeVar

from shared.ports.cache_port import CachePort
from shared.ports.market_data_port import MarketDataPort
from shared.utils.cache_keys import make_cache_key
from shared.utils.time_processor import TimeProcessor

_FetchResult = TypeVar("_FetchResult")

_DEFAULT_MAX_WORKERS = 5
_MAX_WORKERS_CEILING = 16
_TIMEOUT_SECONDS = 30


class BaseService:
    """Strict DI base — cache is required, market_data optional for price-based services."""

    def __init__(self, logger_name: str, cache: CachePort, market_data: MarketDataPort | None = None) -> None:
        self.logger = logging.getLogger(logger_name)
        self._cache: CachePort = cache
        self._market_data: MarketDataPort | None = market_data

    def for_each_ticker(
        self,
        tickers: list[str],
        fetch_fn: Callable[[str], dict[str, Any]],
        max_workers: int = _DEFAULT_MAX_WORKERS,
    ) -> dict[str, Any]:
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
                    except FuturesTimeoutError:
                        self.logger.error("Timeout for %s after %ss", ticker, _TIMEOUT_SECONDS)
                        results[ticker] = {"error": f"Timeout fetching {ticker}"}
                    except Exception as e:
                        self.logger.error("Failed for %s: %s", ticker, e)
                        results[ticker] = {"error": str(e)}
            except FuturesTimeoutError:
                self.logger.error("Overall timeout waiting for ticker futures")
                executor.shutdown(wait=False, cancel_futures=True)
        return results

    def _build_time_params(
        self,
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        years: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[str, str]:
        time_processor = TimeProcessor()
        time_query: dict[str, Any] = {}
        if days is not None:
            time_query["days"] = days
        if weeks is not None:
            time_query["weeks"] = weeks
        if months is not None:
            time_query["months"] = months
        if years is not None:
            time_query["years"] = years
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
        if not tickers or len(tickers) < min_count:
            msg = f"Need at least {min_count} ticker(s)" if min_count > 1 else "Missing ticker"
            self.logger.error(msg)
            return {"error": msg}
        return None

    def _cached_fetch(
        self,
        namespace: str,
        ticker: str,
        fetch_fn: Callable[[], _FetchResult],
        ttl_hours: int = 24,
        **extra_key_parts: Any,
    ) -> _FetchResult:
        cache_key = make_cache_key(namespace, ticker, **extra_key_parts)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore
        result = fetch_fn()
        if isinstance(result, dict) and "error" not in result:
            self._cache.set(cache_key, result, ttl_hours=ttl_hours)
        return result

    def _get_cache_manager(self) -> CachePort:
        return self._cache

    def _fetch_single(self, ticker: str, start_date: str, end_date: str) -> dict[str, Any]:
        """Fetch price data via MarketDataPort — strict, no infrastructure fallback."""
        if self._market_data is None:
            self.logger.error("MarketDataPort not injected for %s", ticker)
            return {"error": "Market data unavailable — DI not wired"}
        try:
            data = self._market_data.get_price_data(ticker, start_date, end_date)
            if data and "error" not in data:
                return data
            self.logger.warning("No data for %s", ticker)
            return {"error": f"No data for {ticker}"}
        except Exception as e:
            self.logger.error("Failed to fetch data for %s: %s", ticker, e)
            return {"error": str(e)}
