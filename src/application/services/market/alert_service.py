from typing import Any
from datetime import datetime, timedelta, timezone

from infrastructure.api_clients.vn_stock_client import VNStockClient
from shared.base_service import BaseService


class AlertService(BaseService):
    def __init__(self) -> None:
        """Khởi tạo AlertService."""
        super().__init__("alert_service")

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
        """Kiểm tra cảnh báo giá cho một mã chứng khoán.

        Args:
            ticker: Mã chứng khoán.
            threshold: Ngưỡng giá.
            condition: Điều kiện (above, below).
            timeframe: Khung thời gian.

        Returns:
            Dict chứa trạng thái cảnh báo và giá hiện tại.
        """
        client = VNStockClient(ticker=ticker)
        end_date = datetime.now(timezone.utc)
        _TIMEFRAME_LOOKBACK = {"1d": 1, "5d": 5, "1w": 7, "2w": 14, "1m": 30, "3m": 90}
        lookback = _TIMEFRAME_LOOKBACK.get(timeframe, 7)
        start_date = end_date - timedelta(days=lookback)
        data = client.fetch_trading_data(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d",
        )

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


_alert_service = AlertService()


def handle_alert_query(
    tickers: list[str],
    threshold: float,
    condition: str = "above",
    timeframe: str = "1d",
) -> dict[str, Any]:
    """Truy vấn cảnh báo giá cho một hoặc nhiều mã chứng khoán.

    Args:
        tickers: Danh sách mã chứng khoán.
        threshold: Ngưỡng giá để so sánh.
        condition: Điều kiện cảnh báo (above, below).
        timeframe: Khung thời gian.

    Returns:
        Dict chứa kết quả cảnh báo cho từng mã.
    """
    return _alert_service.handle_query(
        tickers=tickers,
        threshold=threshold,
        condition=condition,
        timeframe=timeframe,
    )
