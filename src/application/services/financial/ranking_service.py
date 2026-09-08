from typing import Any
from shared.base_service import BaseService
from shared.ports.cache_port import CachePort
from shared.ports.market_data_port import MarketDataPort
from shared.utils.calculations import calculate_std_dev
from shared.utils.stats_helpers import aggregate_values, extract_field_values


class RankingService(BaseService):
    def __init__(self, cache: CachePort, market_data: MarketDataPort) -> None:
        super().__init__("ranking_service", cache, market_data)

    def handle_query(
        self,
        tickers: list[str],
        field: str = "close",
        aggregate: str = "max",
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        err = self._require_tickers(tickers, min_count=2)
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

            self.logger.info(
                f"Ranking {len(tickers)} tickers by {field} ({aggregate}) from {start_date} to {end_date}"
            )

            all_data = self.for_each_ticker(
                tickers, lambda t: self._fetch_single(t, start_date, end_date)
            )

            ranking_results = perform_ranking(all_data, field, aggregate)

            return {
                "ranking": ranking_results,
                "tickers": tickers,
                "requested_field": field,
                "aggregate": aggregate,
                "time_range": {"start_date": start_date, "end_date": end_date},
            }
        except Exception as e:
            self.logger.error(f"Ranking query failed: {e}")
            return {"error": str(e)}








def perform_ranking(all_data: dict[str, Any], field: str, aggregate: str) -> dict[str, Any]:
    """Xếp hạng các mã chứng khoán dựa trên giá trị trường dữ liệu.

    Args:
        all_data: Dict chứa dữ liệu giá của từng mã.
        field: Trường dữ liệu dùng để xếp hạng.
        aggregate: Hàm tổng hợp (max, min, mean, latest).

    Returns:
        Dict chứa bảng xếp hạng và thống kê.
    """
    ticker_stats: dict[str, Any] = {}
    for ticker, data in all_data.items():
        if "error" in data:
            ticker_stats[ticker] = {"error": data["error"]}
            continue

        values = extract_field_values(data.get("data", []), field)
        if values:
            stat_value = aggregate_values(values, aggregate)
            ticker_stats[ticker] = {
                "value": stat_value,
                "count": len(values),
                "data_points": values,
            }

    valid_stats = {k: v for k, v in ticker_stats.items() if "error" not in v}

    if not valid_stats:
        return {"error": "No valid data for ranking"}

    sorted_tickers = sorted(
        valid_stats.items(), key=lambda x: x[1]["value"], reverse=(aggregate != "min")
    )

    ranking_list = []
    for i, (ticker, stats) in enumerate(sorted_tickers, 1):
        ranking_list.append(
            {"rank": i, "ticker": ticker, "value": stats["value"], "data_points": stats["count"]}
        )

    top_performer = ranking_list[0] if ranking_list else None
    bottom_performer = ranking_list[-1] if ranking_list else None

    values = [stats["value"] for stats in valid_stats.values()]
    stats_summary = {
        "mean": sum(values) / len(values) if values else 0,
        "median": sorted(values)[len(values) // 2] if values else 0,
        "std_dev": calculate_std_dev(values) if values else 0,
        "range": (max(values) - min(values)) if values else 0,
    }

    ranking = {
        "ranking_list": ranking_list,
        "top_performer": top_performer,
        "bottom_performer": bottom_performer,
        "total_tickers": len(valid_stats),
        "valid_tickers": list(valid_stats.keys()),
        "statistics": stats_summary,
        "field": field,
        "aggregate": aggregate,
    }

    return ranking

def handle_ranking_query(tickers: list[str],
    field: str = "close",
    aggregate: str = "max",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,) -> dict[str, Any]:
    from shared.service_helpers import call_service
    return call_service("ranking", tickers=tickers, field=field, aggregate=aggregate, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)

