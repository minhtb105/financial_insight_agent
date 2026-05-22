from datetime import datetime, timedelta, timezone
from typing import Any


class TimeProcessor:
    def __init__(self, now: datetime | None = None):
        self._now = now or datetime.now(timezone.utc)

    def process_time_params(self, parsed_query: dict[str, Any]) -> dict[str, Any]:
        from domain.entities.time_range import TimeRange

        tr = TimeRange(
            **{
                k: parsed_query[k]
                for k in ("start", "end", "days", "weeks", "months", "years")
                if parsed_query.get(k) is not None
            }
        )
        resolved = tr.resolve(now=self._now)

        if not self.validate_time_range(resolved["start"], resolved["end"]):
            raise ValueError(
                f"Invalid time range: start={resolved['start']}, end={resolved['end']}. "
                f"Expected start ≤ end, dates within last 10 years, and YYYY-MM-DD format."
            )

        return {
            "start_date": resolved["start"],
            "end_date": resolved["end"],
            "original_params": {
                "start": parsed_query.get("start"),
                "end": parsed_query.get("end"),
                "days": parsed_query.get("days"),
                "weeks": parsed_query.get("weeks"),
                "months": parsed_query.get("months"),
                "years": parsed_query.get("years"),
            },
        }

    def validate_time_range(self, start_date: str, end_date: str) -> bool:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            if end < start:
                return False

            now = self._now
            if end > now:
                return False

            ten_years_ago = now - timedelta(days=365 * 10 + 3)  # accounts for ~3 leap days
            return not start < ten_years_ago

        except ValueError:
            return False

    def get_default_time_range(self) -> dict[str, str]:
        end_date = self._now
        start_date = end_date - timedelta(days=30)

        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }

    @staticmethod
    def calculate_business_days(start_date: str, end_date: str) -> int:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            business_days = 0
            current = start

            while current <= end:
                if current.weekday() < 5:
                    business_days += 1
                current += timedelta(days=1)

            return business_days

        except ValueError:
            return 0

    @staticmethod
    def format_time_range(start_date: str, end_date: str) -> str:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            if start.date() == end.date():
                return start.strftime("%d/%m/%Y")
            else:
                return f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"

        except ValueError:
            return "Invalid date range"

    @staticmethod
    def adjust_for_market_hours(date_str: str) -> dict[str, str]:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")

            market_open = date.replace(hour=9, minute=0, second=0, microsecond=0)
            market_close = date.replace(hour=15, minute=0, second=0, microsecond=0)

            return {
                "market_open": market_open.strftime("%Y-%m-%d %H:%M:%S"),
                "market_close": market_close.strftime("%Y-%m-%d %H:%M:%S"),
            }

        except ValueError:
            return {"error": "Invalid date format"}

    @staticmethod
    def get_relative_time_description(start_date: str, end_date: str) -> str:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            diff = end - start

            if diff.days == 0:
                return "Hôm nay"
            elif diff.days == 1:
                return "1 ngày"
            elif diff.days <= 7:
                return f"{diff.days} ngày"
            elif diff.days <= 30:
                weeks = diff.days // 7
                return f"{weeks} tuần"
            elif diff.days <= 365:
                months = diff.days // 30
                return f"{months} tháng"
            else:
                years = diff.days // 365
                return f"{years} năm"

        except ValueError:
            return "Khoảng thời gian không xác định"



