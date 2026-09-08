from typing import Any

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
        years: int | None = None,
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
            years: Số năm gần nhất.
            start_date: Ngày bắt đầu (YYYY-MM-DD).
            end_date: Ngày kết thúc (YYYY-MM-DD).

        Returns:
            Dict chứa kết quả giá cho từng mã.
        """
        err = self._require_tickers(tickers)
        if err:
            return err

        try:
            start_date_r, end_date_r = self._build_time_params(
                days=days, weeks=weeks, months=months, years=years, start_date=start_date, end_date=end_date
            )
        except ValueError as e:
            return {"error": str(e)}

        results = self.for_each_ticker(tickers, lambda t: self._fetch_price_for_ticker(t, field, start_date_r, end_date_r))

        return results if results else {"error": "No valid data found"}

    def _fetch_price_for_ticker(self, ticker: str, field: str, start_date: str, end_date: str) -> dict[str, Any]:
        """Lấy dữ liệu giá cho một mã chứng khoán.

        Args:
            ticker: Mã chứng khoán.
            field: Trường giá cần lấy.
            start_date: Ngày bắt đầu đã resolve (YYYY-MM-DD).
            end_date: Ngày kết thúc đã resolve (YYYY-MM-DD).

        Returns:
            Dict chứa dữ liệu giá hoặc lỗi.
        """
        try:

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

    # Backward compat alias — old code called _fetch_single(ticker, field, parsed)
    def _fetch_single(self, ticker: str, field: str | dict[str, Any], parsed: dict[str, Any] | None = None) -> dict[str, Any]:
        if isinstance(field, dict) and parsed is None:
            # legacy: _fetch_single(ticker, parsed_dict) — not used anymore
            return {"error": "deprecated _fetch_single signature"}
        if parsed is not None and isinstance(parsed, dict):
            # legacy: _fetch_single(ticker, field, parsed)
            try:
                start_date, end_date = self._build_time_params(
                    days=parsed.get("days"),
                    weeks=parsed.get("weeks"),
                    months=parsed.get("months"),
                    years=parsed.get("years"),
                    start_date=parsed.get("start"),
                    end_date=parsed.get("end"),
                )
            except ValueError as e:
                return {"error": str(e)}
            return self._fetch_price_for_ticker(ticker, field, start_date, end_date)  # type: ignore[arg-type]
        # new signature via BaseService compatibility
        return super()._fetch_single(ticker, field, parsed or "")  # type: ignore[arg-type]

def handle_price_query(tickers: list[str],
    field: str = "close",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    years: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,) -> dict[str, Any]:
    from shared.service_helpers import call_service
    return call_service("price", tickers=tickers, field=field, days=days, weeks=weeks, months=months, years=years, start_date=start_date, end_date=end_date)

