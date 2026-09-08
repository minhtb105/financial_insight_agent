import logging
from typing import Any
import math
from shared.base_service import BaseService
from shared.ports.market_data_port import MarketDataPort
from shared.ports.cache_port import CachePort


class CompareService(BaseService):
    def __init__(self, cache: CachePort, market_data: MarketDataPort) -> None:
        """Khởi tạo CompareService — strict DI."""
        super().__init__("CompareService", cache, market_data)

    def handle_query(
        self,
        tickers: list[str],
        compare_with: list[str],
        field: str = "close",
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        err = self._require_tickers(tickers)
        if err:
            return err
        if not compare_with:
            self.logger.error("Missing compare_with parameter")
            return {"error": "Missing compare_with parameter"}

        try:
            start_date, end_date = self._build_time_params(
                days=days,
                weeks=weeks,
                months=months,
                start_date=start_date,
                end_date=end_date,
            )

            main_data = self.for_each_ticker(
                tickers,
                lambda t: self._fetch_single(t, start_date, end_date),
            )
            compare_data = self.for_each_ticker(
                compare_with,
                lambda t: self._fetch_single(t, start_date, end_date),
            )

            comparison_results = perform_comparison(main_data, compare_data, field)

            return {
                "comparison": comparison_results,
                "main_tickers": tickers,
                "compare_tickers": compare_with,
                "requested_field": field,
                "time_range": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
            }

        except Exception as e:
            self.logger.error(f"Compare query failed: {e}")
            return {"error": str(e)}








def perform_comparison(
    main_data: dict[str, Any],
    compare_data: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    """So sánh dữ liệu giá giữa hai nhóm mã chứng khoán.

    Args:
        main_data: Dữ liệu giá của nhóm chính.
        compare_data: Dữ liệu giá của nhóm so sánh.
        field: Trường dữ liệu cần so sánh.

    Returns:
        Dict chứa kết quả so sánh (thống kê, chênh lệch).
    """
    comparison = {}

    main_stats = {}
    for ticker, data in main_data.items():
        if "error" in data:
            main_stats[ticker] = {"error": data["error"]}
            continue

        values = [
            item[field]
            for item in data["data"]
            if field in item and item.get(field) is not None and item[field] == item[field]
        ]
        if values:
            main_stats[ticker] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1] if values else None,
                "count": len(values),
            }

    compare_stats = {}
    for ticker, data in compare_data.items():
        if "error" in data:
            compare_stats[ticker] = {"error": data["error"]}
            continue

        values = [
            item[field]
            for item in data["data"]
            if field in item and item.get(field) is not None and item[field] == item[field]
        ]
        if values:
            compare_stats[ticker] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1] if values else None,
                "count": len(values),
            }

    main_overall = calculate_overall_stats(main_stats)
    compare_overall = calculate_overall_stats(compare_stats)

    percentage_diff = calculate_percentage_difference(main_overall, compare_overall)

    comparison = {
        "main_tickers_stats": main_stats,
        "compare_tickers_stats": compare_stats,
        "main_overall": main_overall,
        "compare_overall": compare_overall,
        "percentage_difference": percentage_diff,
        "field": field,
    }

    return comparison


def calculate_overall_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """Tính thống kê tổng hợp từ nhiều mã chứng khoán.

    Args:
        stats: Dict chứa thống kê của từng mã.

    Returns:
        Dict chứa các chỉ số tổng hợp (mean, min, max, latest_mean).
    """
    valid_stats = {k: v for k, v in stats.items() if "error" not in v}

    if not valid_stats:
        return {"error": "No valid data for calculation"}

    total_mean = sum(stat["mean"] for stat in valid_stats.values())
    overall_mean = total_mean / len(valid_stats)

    all_mins = [stat["min"] for stat in valid_stats.values()]
    all_maxs = [stat["max"] for stat in valid_stats.values()]

    overall_min = min(all_mins)
    overall_max = max(all_maxs)

    latest_values = [stat["latest"] for stat in valid_stats.values() if stat["latest"] is not None]
    latest_mean = sum(latest_values) / len(latest_values) if latest_values else None

    return {
        "mean": overall_mean,
        "min": overall_min,
        "max": overall_max,
        "latest_mean": latest_mean,
        "tickers_count": len(valid_stats),
        "total_data_points": sum(stat["count"] for stat in valid_stats.values()),
    }


def calculate_percentage_difference(
    main_stats: dict[str, Any], compare_stats: dict[str, Any]
) -> dict[str, Any]:
    """Tính phần trăm chênh lệch giữa hai bộ thống kê.

    Args:
        main_stats: Thống kê tổng hợp của nhóm chính.
        compare_stats: Thống kê tổng hợp của nhóm so sánh.

    Returns:
        Dict chứa phần trăm chênh lệch cho từng chỉ số.
    """
    if "error" in main_stats or "error" in compare_stats:
        return {"error": "Cannot calculate percentage difference with invalid data"}

    diff = {}

    for metric in ["mean", "min", "max", "latest_mean"]:
        if metric in main_stats and metric in compare_stats:
            main_val = main_stats[metric]
            compare_val = compare_stats[metric]

            if compare_val != 0 and not math.isnan(compare_val) and not math.isnan(main_val):
                percentage = ((main_val - compare_val) / compare_val) * 100
                diff[metric] = {
                    "main": main_val,
                    "compare": compare_val,
                    "difference": main_val - compare_val,
                    "percentage": percentage,
                }

    return diff

def handle_compare_query(tickers: list[str],
    compare_with: list[str],
    field: str = "close",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,) -> dict[str, Any]:
    from shared.service_registry import get_service
    svc = get_service("compare")
    if svc is None:
        raise RuntimeError("Service 'compare' not initialized — call init_deps()")
    return svc.handle_query(tickers=tickers, compare_with=compare_with, field=field, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)

