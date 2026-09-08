import logging
from typing import Any

from shared.utils.time_processor import TimeProcessor
from domain.schemas.price import PriceRecord, PriceResult
from shared.base_service import BaseService
from shared.ports.market_data_port import MarketDataPort
from shared.ports.cache_port import CachePort


class PriceService(BaseService):
    def __init__(self, cache: CachePort, market_data: MarketDataPort) -> None:
        """Khởi tạo PriceService — strict DI."""
        super().__init__("price_service", cache, market_data)

    def handle_query(
        self,
        tickers: list[str],
        field: str = "close",
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Truy vấn dữ liệu giá cho danh sách mã chứng khoán.

        Args:
            tickers: Danh sách mã chứng khoán.
            field: Trường giá cần lấy.
            days: Số ngày gần nhất.
            weeks: Số tuần gần nhất.
            months: Số tháng gần nhất.
            start_date: Ngày bắt đầu (YYYY-MM-DD).
            end_date: Ngày kết thúc (YYYY-MM-DD).

        Returns:
            Dict chứa kết quả giá cho từng mã.
        """
        err = self._require_tickers(tickers)
        if err:
            return err

        parsed: dict[str, Any] = {
            "tickers": tickers,
            "requested_field": field,
        }
        if days is not None:
            parsed["days"] = days
        if weeks is not None:
            parsed["weeks"] = weeks
        if months is not None:
            parsed["months"] = months
        if start_date is not None:
            parsed["start"] = start_date
        if end_date is not None:
            parsed["end"] = end_date

        results = self.for_each_ticker(tickers, lambda t: self._fetch_single(t, field, parsed))

        return results if results else {"error": "No valid data found"}

    def _fetch_single(self, ticker: str, field: str, parsed: dict[str, Any]) -> dict[str, Any]:
        """Lấy dữ liệu giá cho một mã chứng khoán.

        Args:
            ticker: Mã chứng khoán.
            field: Trường giá cần lấy.
            parsed: Dict chứa tham số thời gian đã xử lý.

        Returns:
            Dict chứa dữ liệu giá hoặc lỗi.
        """
        try:
            time_processor = TimeProcessor()
            time_params = time_processor.process_time_params(parsed)
            start_date = time_params["start_date"]
            end_date = time_params["end_date"]

            raw = self._market_data.get_price_data(ticker, start_date, end_date)
            if "error" in raw:
                return raw

            records = []
            for item in raw.get("data", []):
                record = PriceRecord(date=item["date"])
                if field in ("ohlcv", "open") and not BaseService._is_nan(item.get("open")):
                    record.open_price = float(item["open"])
                if field in ("ohlcv", "high") and not BaseService._is_nan(item.get("high")):
                    record.high = float(item["high"])
                if field in ("ohlcv", "low") and not BaseService._is_nan(item.get("low")):
                    record.low = float(item["low"])
                if field in ("ohlcv", "close") and not BaseService._is_nan(item.get("close")):
                    record.close = float(item["close"])
                if field in ("ohlcv", "volume") and not BaseService._is_nan(item.get("volume")):
                    record.volume = int(item["volume"])
                records.append(record)

            return PriceResult(
                ticker=ticker,
                data=records,
                start_date=start_date,
                end_date=end_date,
            ).model_dump()

        except Exception as e:
            self.logger.error(f"Failed to fetch price for {ticker}: {e}")
            return {"error": str(e)}

def handle_price_query(tickers: list[str],
    field: str = "close",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,) -> dict[str, Any]:
    from shared.service_registry import get_service
    svc = get_service("price")
    if svc is None:
        raise RuntimeError("Service 'price' not initialized — call init_deps()")
    return svc.handle_query(tickers=tickers, field=field, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)

