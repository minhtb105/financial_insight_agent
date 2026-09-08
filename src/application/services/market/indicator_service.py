import json
from typing import Any
import pandas as pd
from shared.constants import INDICATOR_TTL_HOURS
from shared.utils.cache_keys import make_cache_key
from shared.base_service import BaseService
from shared.ports.market_data_port import MarketDataPort
from shared.ports.cache_port import CachePort


_INDICATOR_REGISTRY: dict[str, dict[str, Any]] = {
    "sma": {
        "default_params": [20],
        "calc_fn": lambda data, p: calculate_sma(data, p),
        "key_fn": lambda p: f"sma_{p}",
    },
    "rsi": {
        "default_params": [14],
        "calc_fn": lambda data, p: calculate_rsi(data, p),
        "key_fn": lambda p: f"rsi_{p}",
    },
    "macd": {
        "default_params": [(12, 26)],
        "calc_fn": lambda data, p: calculate_macd(data, p[0], p[1]),
        "key_fn": lambda p: f"macd_{p[0]}_{p[1]}",
    },
}


class IndicatorService(BaseService):
    def __init__(self, cache: CachePort, market_data: MarketDataPort) -> None:
        """Khởi tạo IndicatorService — strict DI."""
        super().__init__("indicator_service", cache, market_data)

    def handle_query(
        self,
        tickers: list[str],
        indicator_params: dict[str, Any] | None = None,
        field: str = "sma",
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        err = self._require_tickers(tickers)
        if err:
            return err
        results = self.for_each_ticker(
            tickers,
            lambda t: self._fetch_single(
                t,
                indicator_params=indicator_params,
                requested_field=field,
                days=days,
                weeks=weeks,
                months=months,
                start_date=start_date,
                end_date=end_date,
            ),
        )
        return results

    def _fetch_single(
        self,
        ticker: str,
        indicator_params: dict[str, Any] | None = None,
        requested_field: str = "sma",
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        indicator_params = indicator_params or {}

        try:
            start_date, end_date = self._build_time_params(
                days=days,
                weeks=weeks,
                months=months,
                start_date=start_date,
                end_date=end_date,
            )

            cache = self._cache
            ip_str = json.dumps(indicator_params, sort_keys=True) if indicator_params else ""
            cache_key = make_cache_key(
                "indicator",
                ticker,
                start_date,
                end_date,
                requested_field=requested_field,
                indicator_params=ip_str,
            )
            cached = cache.get(cache_key) if cache else None
            if cached is not None:
                return cached

            result = self._market_data.get_price_data(ticker, start_date, end_date)
            if result is None or "error" in result or not result.get("data"):
                return {"error": "No data available"}
            import pandas as pd

            data = pd.DataFrame(result["data"])

            if data is None or data.empty:
                return {"error": "No data available"}

            ticker_results = {}

            for name, cfg in _INDICATOR_REGISTRY.items():
                if requested_field == name or (indicator_params and name in indicator_params):
                    params = indicator_params.get(name, cfg["default_params"]) if indicator_params else cfg["default_params"]
                    for p in params:
                        ticker_results[cfg["key_fn"](p)] = cfg["calc_fn"](data, p)

            if cache:
                cache.set(cache_key, ticker_results, ttl_hours=INDICATOR_TTL_HOURS)
            return ticker_results

        except Exception as e:
            self.logger.error(f"Failed for {ticker}: {e}")
            return {"error": str(e)}







def _fmt_date(value: Any) -> str:
    """Normalize date cell (str or datetime-like) to YYYY-MM-DD."""
    if isinstance(value, str):
        return value[:10]
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def calculate_sma(data: pd.DataFrame, period: int) -> list[dict[str, Any]]:
    """Tính đường trung bình động đơn giản (SMA) từ dữ liệu giá.

    Args:
        data: DataFrame chứa dữ liệu giá.
        period: Số kỳ tính SMA.

    Returns:
        Danh sách dict chứa giá trị SMA theo ngày.
    """
    if len(data) < period:
        return []

    close_prices = data["close"].astype(float)
    sma_values = close_prices.rolling(window=period).mean()

    result = []
    for date, sma in zip(data["date"], sma_values, strict=False):
        if pd.notna(sma):
            result.append({"date": _fmt_date(date), "sma": float(sma)})

    return result


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> list[dict[str, Any]]:
    """Tính chỉ báo RSI từ dữ liệu giá.

    Args:
        data: DataFrame chứa dữ liệu giá.
        period: Số kỳ tính RSI.

    Returns:
        Danh sách dict chứa giá trị RSI theo ngày.
    """
    if len(data) < period + 1:
        return []

    close_prices = data["close"].astype(float)

    delta = close_prices.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    result = []
    for date, rsi_val in zip(data["date"], rsi, strict=False):
        if pd.notna(rsi_val):
            result.append({"date": _fmt_date(date), "rsi": float(rsi_val)})

    return result


def calculate_macd(
    data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26
) -> list[dict[str, Any]]:
    """Tính chỉ báo MACD từ dữ liệu giá.

    Args:
        data: DataFrame chứa dữ liệu giá.
        fast_period: Số kỳ EMA nhanh.
        slow_period: Số kỳ EMA chậm.

    Returns:
        Danh sách dict chứa giá trị MACD, signal và histogram theo ngày.
    """
    if len(data) < slow_period:
        return []

    close_prices = data["close"].astype(float)

    ema_fast = close_prices.ewm(span=fast_period).mean()
    ema_slow = close_prices.ewm(span=slow_period).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line

    result = []
    for i, date in enumerate(data["date"]):
        has_macd = pd.notna(macd_line.iloc[i])
        has_signal = pd.notna(signal_line.iloc[i])
        has_histogram = pd.notna(histogram.iloc[i])
        if has_macd or has_signal or has_histogram:
            entry: dict[str, Any] = {"date": _fmt_date(date)}
            if has_macd:
                entry["macd"] = float(macd_line.iloc[i])
            if has_signal:
                entry["signal"] = float(signal_line.iloc[i])
            if has_histogram:
                entry["histogram"] = float(histogram.iloc[i])
            result.append(entry)

    return result

def handle_indicator_query(
    tickers: list[str],
    indicator: str = "sma",
    period: int | None = None,
    fast_period: int | None = None,
    slow_period: int | None = None,
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    from shared.service_helpers import call_service
    # Map indicator -> field + indicator_params (kept for backward compat with MCP tools)
    indicator_params: dict[str, Any] | None = {}
    if period is not None:
        indicator_params["period"] = period
    if fast_period is not None:
        indicator_params["fast_period"] = fast_period
    if slow_period is not None:
        indicator_params["slow_period"] = slow_period
    if not indicator_params:
        indicator_params = None
    return call_service(
        "indicator",
        tickers=tickers,
        field=indicator,
        indicator_params=indicator_params,
        days=days,
        weeks=weeks,
        months=months,
        start_date=start_date,
        end_date=end_date,
    )

