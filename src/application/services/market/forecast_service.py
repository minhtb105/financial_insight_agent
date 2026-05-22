from typing import Any
from statistics import mean, stdev
from datetime import datetime, timedelta, timezone

from shared.constants import FORECAST_TTL_HOURS
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key
from shared.base_service import BaseService

_TIMEFRAME_DAYS = {
    "1d": 1,
    "5d": 5,
    "1w": 7,
    "2w": 14,
    "1m": 30,
}


class ForecastService(BaseService):
    def __init__(self) -> None:
        """Khởi tạo ForecastService."""
        super().__init__("forecast_service")

    def handle_query(
        self,
        tickers: list[str],
        timeframe: str = "1w",
    ) -> dict[str, Any]:
        """Truy vấn dự báo giá cho danh sách mã chứng khoán.

        Args:
            tickers: Danh sách mã chứng khoán.
            timeframe: Khung thời gian dự báo.

        Returns:
            Dict chứa kết quả dự báo cho từng mã.
        """
        err = self._require_tickers(tickers)
        if err:
            return err

        results = self.for_each_ticker(tickers, lambda t: self._forecast_single(t, timeframe))

        return {
            "forecasts": results,
            "model": "simple_moving_average",
            "timeframe": timeframe,
        }

    def _forecast_single(self, ticker: str, timeframe: str) -> dict[str, Any]:
        """Dự báo giá cho một mã chứng khoán dựa trên SMA.

        Args:
            ticker: Mã chứng khoán.
            timeframe: Khung thời gian dự báo.

        Returns:
            Dict chứa kết quả dự báo hoặc lỗi.
        """
        cache = get_cache_manager()
        cache_key = make_cache_key("forecast", ticker, timeframe)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        client = VNStockClient(ticker=ticker)
        end_date = datetime.now(timezone.utc)
        lookback = _TIMEFRAME_DAYS.get(timeframe, 180)
        min_lookback = max(lookback, 20)
        start_date = end_date - timedelta(days=min_lookback)
        data = client.fetch_trading_data(
            start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="1d"
        )

        if data is None or data.empty or len(data) < 20:
            return {"error": "Insufficient historical data for forecast"}

        if "close" not in data.columns:
            return {"error": "Missing 'close' column in price data"}
        close_prices = [c for c in data["close"].dropna().astype(float).tolist() if c == c]
        if len(close_prices) < 20:
            return {"error": "Insufficient clean data for forecast"}
        n = len(close_prices)
        sma_20 = mean(close_prices[-20:])
        prev_price = close_prices[-5]
        recent_trend = (
            (close_prices[-1] - prev_price) / prev_price if n >= 5 and prev_price != 0 else 0.0
        )
        volatility = stdev(close_prices[-20:]) if n >= 20 else 0.0

        last_price = close_prices[-1]
        projected_price = last_price * (1 + recent_trend)
        confidence_bound = volatility * 1.96

        forecast = {
            "ticker": ticker,
            "last_price": round(last_price, 2),
            "projected_price": round(projected_price, 2),
            "confidence_bounds": {
                "lower": round(projected_price - confidence_bound, 2),
                "upper": round(projected_price + confidence_bound, 2),
                "note": "Simple SMA-based estimate, not a statistical confidence interval",
            },
            "volatility": round(volatility, 4),
            "trend_pct": round(recent_trend * 100, 2),
            "sma_20": round(sma_20, 2),
            "data_points": n,
            "timeframe": timeframe,
        }

        if cache:
            cache.set(cache_key, forecast, ttl_hours=FORECAST_TTL_HOURS)
        return forecast


_forecast_service = ForecastService()


def handle_forecast_query(
    tickers: list[str],
    timeframe: str = "1w",
) -> dict[str, Any]:
    """Truy vấn dự báo giá cho một hoặc nhiều mã chứng khoán.

    Args:
        tickers: Danh sách mã chứng khoán.
        timeframe: Khung thời gian dự báo (vd: "1w", "1m").

    Returns:
        Dict chứa kết quả dự báo cho từng mã.
    """
    return _forecast_service.handle_query(tickers=tickers, timeframe=timeframe)
