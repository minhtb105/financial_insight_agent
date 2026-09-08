from typing import Any
from shared.base_service import BaseService
from shared.ports.cache_port import CachePort
from shared.ports.market_data_port import MarketDataPort
from shared.utils.calculations import calculate_std_dev
from shared.utils.stats_helpers import aggregate_values, extract_field_values


class AggregateService(BaseService):
    def __init__(self, cache: CachePort, market_data: MarketDataPort) -> None:
        super().__init__("aggregate_service", cache, market_data)

    def handle_query(
        self,
        tickers: list[str],
        field: str = "close",
        aggregate: str = "mean",
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        err = self._require_tickers(tickers)
        if err:
            return err

        try:
            start_date, end_date = self._build_time_params(
                days=days,
                weeks=weeks,
                months=months,
                start_date=start_date,
                end_date=end_date,
            )

            self.logger.info(f"Fetching data for {len(tickers)} ticker(s)")

            all_data = self.for_each_ticker(
                tickers,
                lambda t: self._fetch_single(t, start_date, end_date),
            )

            if len(all_data) == 1 and "error" in all_data:
                return all_data

            aggregate_results = perform_aggregation(all_data, field, aggregate)

            return {
                "aggregation": aggregate_results,
                "tickers": tickers,
                "requested_field": field,
                "aggregate": aggregate,
                "time_range": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
            }

        except Exception as e:
            self.logger.error(f"Aggregation failed: {e}")
            return {"error": str(e)}








def perform_aggregation(
    all_data: dict[str, Any],
    field: str,
    aggregate_func: str,
) -> dict[str, Any]:
    """Tổng hợp dữ liệu giá từ nhiều mã chứng khoán.

    Args:
        all_data: Dict chứa dữ liệu giá của từng mã.
        field: Trường dữ liệu cần tổng hợp.
        aggregate_func: Hàm tổng hợp (mean, sum, median, std, min, max).

    Returns:
        Dict chứa kết quả tổng hợp và thống kê tổng quan.
    """
    all_values: list[float] = []
    ticker_data: dict[str, Any] = {}

    for ticker, data in all_data.items():
        if "error" in data:
            continue
        values = extract_field_values(data.get("data", []), field)
        if values:
            ticker_data[ticker] = {
                "values": values,
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            }
            all_values.extend(values)

    if not all_values:
        return {"error": "No valid data for aggregation"}

    result_value = aggregate_values(all_values, aggregate_func)

    # overall stats via helpers
    sorted_values = sorted(all_values)
    n = len(sorted_values)
    overall_mean = sum(all_values) / n
    overall_median = sorted_values[n // 2] if n % 2 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
    overall_std = calculate_std_dev(all_values)
    cv = (overall_std / overall_mean) * 100 if overall_mean and overall_mean == overall_mean else 0

    aggregation = {
        "result": {
            "function": aggregate_func,
            "value": result_value,
            "field": field,
        },
        "overall_statistics": {
            "mean": overall_mean,
            "median": overall_median,
            "std_dev": overall_std,
            "min": min(all_values),
            "max": max(all_values),
            "sum": sum(all_values),
            "coefficient_of_variation": cv,
            "total_data_points": len(all_values),
        },
        "ticker_breakdown": ticker_data,
        "valid_tickers": list(ticker_data.keys()),
        "total_tickers": len(ticker_data),
    }

    return aggregation

def handle_aggregate_query(tickers: list[str],
    field: str = "close",
    aggregate: str = "mean",
    aggregate_fn: str | None = None,
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,) -> dict[str, Any]:
    from shared.service_helpers import call_service
    # Support both param names for backward compat (tool used aggregate_fn, service uses aggregate)
    agg = aggregate_fn if aggregate_fn is not None else aggregate
    return call_service("aggregate", tickers=tickers, field=field, aggregate=agg, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)

