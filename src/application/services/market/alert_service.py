import logging
from typing import Any
from datetime import datetime, timedelta, timezone

from shared.base_service import BaseService
from shared.ports.market_data_port import MarketDataPort
from shared.ports.cache_port import CachePort


class AlertService(BaseService):
    def __init__(self, cache: CachePort, market_data: MarketDataPort) -> None:
        super().__init__("alert_service", cache, market_data)

    def handle_query(
        self,
        tickers: list[str],
        threshold: float,
        condition: str = "above",
        timeframe: str = "1d",
    ) -> dict[str, Any]:
        """Truy vấn cảnh báo giá cho danh sách mã chứng khoán.

        Args:
            tickers: Danh sách mã chứng khoán.
            threshold: Ngưỡng giá.
            condition: Điều kiện (above, below).
            timeframe: Khung thời gian.

        Returns:
            Dict chứa danh sách cảnh báo và thông tin tổng hợp.
        """
        err = self._require_tickers(tickers)
        if err:
            return err
        if threshold is None:
            return {"error": "Missing threshold parameter"}

        raw = self.for_each_ticker(
            tickers,
            lambda t: self._check_single(t, threshold, condition, timeframe),
        )

        results = []
        for ticker in tickers:
            entry = raw.get(ticker, {})
            entry["ticker"] = ticker
            results.append(entry)

        return {
            "alerts": results,
            "timeframe": timeframe,
            "summary": {
                "total": len(results),
                "triggered": sum(1 for r in results if r.get("triggered")),
            },
        }

    def _check_single(self, ticker: str, threshold: float, condition: str, timeframe: str = "1d") -> dict[str, Any]:
        end_date = datetime.now(timezone.utc)
        _TIMEFRAME_LOOKBACK = {"1d": 1, "5d": 5, "1w": 7, "2w": 14, "1m": 30, "3m": 90}
        lookback = _TIMEFRAME_LOOKBACK.get(timeframe, 7)
        start_date = end_date - timedelta(days=lookback)
        result = self._market_data.get_price_data(ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        if result is None or "error" in result or not result.get("data"):
            return {"error": "No price data available"}
        import pandas as pd

        data = pd.DataFrame(result["data"])
        if data is None or data.empty or len(data) < 1:
            return {"error": "No price data available"}
        if "close" not in data.columns or data["close"].isna().all():
            return {"error": "Missing close price data"}

        last_close = data.iloc[-1]["close"]
        if last_close is None or last_close != last_close:
            return {"error": "Latest close price is invalid"}
        current_price = float(last_close)
        triggered = (condition == "above" and current_price >= threshold) or (
            condition == "below" and current_price <= threshold
        )

        return {
            "current_price": current_price,
            "threshold": threshold,
            "condition": condition,
            "triggered": triggered,
        }

def handle_alert_query(tickers: list[str],
    threshold: float,
    condition: str = "above",
    timeframe: str = "1d",) -> dict[str, Any]:
    from shared.service_registry import get_service
    svc = get_service("alert")
    if svc is None:
        raise RuntimeError("Service 'alert' not initialized — call init_deps()")
    return svc.handle_query(tickers=tickers, threshold=threshold, condition=condition, timeframe=timeframe)

