from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class TimeProcessor:
    def __init__(self, now: Optional[datetime] = None):
        self._now = now or datetime.now()

    def process_time_params(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        result = {}

        start = parsed_query.get("start")
        end = parsed_query.get("end")
        days = parsed_query.get("days")
        weeks = parsed_query.get("weeks")
        months = parsed_query.get("months")
        years = parsed_query.get("years")

        processed_end = self._process_special_end_value(end)

        if not start and processed_end and (days or weeks or months or years):
            now = self._now
            end_date = datetime.strptime(processed_end, "%Y-%m-%d")

            if days:
                start_date = now - timedelta(days=days)
            elif weeks:
                start_date = now - timedelta(weeks=weeks)
            elif months:
                start_date = self._subtract_months(now, months)
            elif years:
                start_date = now.replace(year=now.year - years)
            else:
                start_date = now - timedelta(days=7)

            if start_date > end_date:
                start_date = end_date

            result["start_date"] = start_date.strftime("%Y-%m-%d")
            result["end_date"] = end_date.strftime("%Y-%m-%d")

        elif start and processed_end:
            result["start_date"] = start
            result["end_date"] = processed_end
        else:
            result = self._fill_missing_time_params(start, processed_end, days, weeks, months, years)

        result["original_params"] = {
            "start": start,
            "end": end,
            "days": days,
            "weeks": weeks,
            "months": months,
            "years": years
        }

        return result

    def _fill_missing_time_params(self, start: str, end: str, days: int, weeks: int, months: int, years: int) -> Dict[str, Any]:
        result = {}
        end_date = self._now

        if end and not start:
            end_date = datetime.strptime(end, "%Y-%m-%d")
            start_date = end_date

            if days:
                start_date = end_date - timedelta(days=days)
            elif weeks:
                start_date = end_date - timedelta(weeks=weeks)
            elif months:
                start_date = self._subtract_months(end_date, months)
            elif years:
                start_date = end_date.replace(year=end_date.year - years)
            else:
                start_date = end_date - timedelta(days=7)

        elif start and not end:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = self._now

            if start_date > end_date:
                end_date = start_date
                start_date = end_date - timedelta(days=7)

        elif not start and not end:
            if days:
                start_date = end_date - timedelta(days=days)
            elif weeks:
                start_date = end_date - timedelta(weeks=weeks)
            elif months:
                start_date = self._subtract_months(end_date, months)
            elif years:
                start_date = end_date.replace(year=end_date.year - years)
            else:
                start_date = end_date - timedelta(days=30)

        else:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")

        result["start_date"] = start_date.strftime("%Y-%m-%d")
        result["end_date"] = end_date.strftime("%Y-%m-%d")

        return result

    @staticmethod
    def _subtract_months(date: datetime, months: int) -> datetime:
        year = date.year - (months // 12)
        month = date.month - (months % 12)

        if month <= 0:
            year -= 1
            month += 12

        day = min(date.day, 31 if month in [1, 3, 5, 7, 8, 10, 12] else 30 if month in [4, 6, 9, 11] else 28)

        return date.replace(year=year, month=month, day=day)

    def _process_special_end_value(self, end: str) -> str:
        if not end:
            return end

        now = self._now

        if end == "yesterday":
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        elif end == "today":
            return now.strftime("%Y-%m-%d")
        elif end == "last_week":
            return (now - timedelta(days=7)).strftime("%Y-%m-%d")
        elif end == "last_month":
            if now.month == 1:
                last_month = now.replace(year=now.year - 1, month=12)
            else:
                last_month = now.replace(month=now.month - 1)

            try:
                last_month_date = last_month.replace(day=now.day)
            except ValueError:
                if last_month.month == 2:
                    if (last_month.year % 4 == 0 and last_month.year % 100 != 0) or (last_month.year % 400 == 0):
                        last_month_date = last_month.replace(day=29)
                    else:
                        last_month_date = last_month.replace(day=28)
                elif last_month.month in [4, 6, 9, 11]:
                    last_month_date = last_month.replace(day=30)
                else:
                    last_month_date = last_month.replace(day=31)

            return last_month_date.strftime("%Y-%m-%d")

        return end

    def validate_time_range(self, start_date: str, end_date: str) -> bool:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            if end < start:
                return False

            now = self._now
            if end > now + timedelta(days=1):
                return False

            ten_years_ago = now - timedelta(days=365 * 10)
            if start < ten_years_ago:
                return False

            return True

        except ValueError:
            return False

    def get_default_time_range(self) -> Dict[str, str]:
        end_date = self._now
        start_date = end_date - timedelta(days=30)

        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
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
    def adjust_for_market_hours(date_str: str) -> Dict[str, str]:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")

            market_open = date.replace(hour=9, minute=0, second=0, microsecond=0)
            market_close = date.replace(hour=15, minute=0, second=0, microsecond=0)

            return {
                "market_open": market_open.strftime("%Y-%m-%d %H:%M:%S"),
                "market_close": market_close.strftime("%Y-%m-%d %H:%M:%S")
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
                return "H\u00f4m nay"
            elif diff.days == 1:
                return "1 ng\u00e0y"
            elif diff.days <= 7:
                return f"{diff.days} ng\u00e0y"
            elif diff.days <= 30:
                weeks = diff.days // 7
                return f"{weeks} tu\u1ea7n"
            elif diff.days <= 365:
                months = diff.days // 30
                return f"{months} th\u00e1ng"
            else:
                years = diff.days // 365
                return f"{years} n\u0103m"

        except ValueError:
            return "Kho\u1ea3ng th\u1eddi gian kh\u00f4ng x\u00e1c \u0111\u1ecbnh"


def process_service_time_params(service_name: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
    time_processor = TimeProcessor()
    processed_time = time_processor.process_time_params(parsed_query)

    if not time_processor.validate_time_range(processed_time["start_date"], processed_time["end_date"]):
        default_time = time_processor.get_default_time_range()
        processed_time["start_date"] = default_time["start_date"]
        processed_time["end_date"] = default_time["end_date"]

    processed_time["service"] = service_name
    processed_time["time_description"] = time_processor.get_relative_time_description(
        processed_time["start_date"],
        processed_time["end_date"]
    )

    return processed_time