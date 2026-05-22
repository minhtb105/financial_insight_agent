from datetime import datetime
from unittest.mock import patch


from shared.utils.time_processor import TimeProcessor


class TestTimeProcessor:
    def setup_method(self):
        self.fixed_now = datetime(2026, 3, 10)
        self.processor = TimeProcessor(now=self.fixed_now)

    def test_calculate_business_days(self):
        result = TimeProcessor.calculate_business_days("2026-03-02", "2026-03-06")
        assert result == 5

    def test_calculate_business_days_includes_weekend(self):
        result = TimeProcessor.calculate_business_days("2026-03-05", "2026-03-09")
        assert result == 3

    def test_calculate_business_days_invalid_date(self):
        assert TimeProcessor.calculate_business_days("invalid", "2026-03-09") == 0

    def test_format_time_range_same_day(self):
        result = TimeProcessor.format_time_range("2026-03-10", "2026-03-10")
        assert result == "10/03/2026"

    def test_format_time_range_different_days(self):
        result = TimeProcessor.format_time_range("2026-03-01", "2026-03-10")
        assert result == "01/03/2026 - 10/03/2026"

    def test_format_time_range_invalid(self):
        assert TimeProcessor.format_time_range("invalid", "2026-03-10") == "Invalid date range"

    def test_adjust_for_market_hours(self):
        result = TimeProcessor.adjust_for_market_hours("2026-03-10")
        assert result["market_open"] == "2026-03-10 09:00:00"
        assert result["market_close"] == "2026-03-10 15:00:00"

    def test_adjust_for_market_hours_invalid(self):
        result = TimeProcessor.adjust_for_market_hours("invalid")
        assert result["error"] == "Invalid date format"

    def test_get_relative_time_description_today(self):
        result = self.processor.get_relative_time_description("2026-03-10", "2026-03-10")
        assert result == "Hôm nay"

    def test_get_relative_time_description_one_day(self):
        result = self.processor.get_relative_time_description("2026-03-09", "2026-03-10")
        assert result == "1 ngày"

    def test_get_relative_time_description_few_days(self):
        result = self.processor.get_relative_time_description("2026-03-05", "2026-03-10")
        assert result == "5 ngày"

    def test_get_relative_time_description_weeks(self):
        result = self.processor.get_relative_time_description("2026-02-17", "2026-03-10")
        assert result == "3 tuần"

    def test_get_relative_time_description_months(self):
        result = self.processor.get_relative_time_description("2025-12-10", "2026-03-10")
        assert result == "3 tháng"

    def test_get_relative_time_description_years(self):
        result = self.processor.get_relative_time_description("2023-03-10", "2026-03-10")
        assert result == "3 năm"

    def test_get_relative_time_description_invalid(self):
        result = self.processor.get_relative_time_description("invalid", "2026-03-10")
        assert result == "Khoảng thời gian không xác định"

    def test_parse_days(self):
        result = self.processor.process_time_params({"days": 7})
        assert result["start_date"] == "2026-03-03"
        assert result["end_date"] == "2026-03-10"

    def test_parse_months(self):
        result = self.processor.process_time_params({"months": 1})
        assert result["start_date"] == "2026-02-10"
        assert result["end_date"] == "2026-03-10"

    def test_parse_weeks(self):
        result = self.processor.process_time_params({"weeks": 3})
        assert result["start_date"] == "2026-02-17"
        assert result["end_date"] == "2026-03-10"

    def test_parse_exact_range(self):
        result = self.processor.process_time_params({"start": "2026-01-01", "end": "2026-01-31"})
        assert result["start_date"] == "2026-01-01"
        assert result["end_date"] == "2026-01-31"

    def test_end_yesterday(self):
        result = self.processor.process_time_params({"end": "yesterday"})
        assert result["end_date"] == "2026-03-09"

    def test_end_today(self):
        result = self.processor.process_time_params({"end": "today"})
        assert result["end_date"] == "2026-03-10"

    def test_end_last_week(self):
        result = self.processor.process_time_params({"end": "last_week"})
        assert result["end_date"] == "2026-03-03"

    def test_end_last_month(self):
        result = self.processor.process_time_params({"end": "last_month"})
        assert result["end_date"] == "2026-02-10"

    def test_end_yesterday_with_days(self):
        result = self.processor.process_time_params({"days": 7})
        assert result["start_date"] == "2026-03-03"

    def test_end_yesterday_with_months(self):
        result = self.processor.process_time_params({"months": 1})
        assert result["start_date"] == "2026-02-10"

    def test_end_yesterday_with_weeks(self):
        result = self.processor.process_time_params({"weeks": 3})
        assert result["start_date"] == "2026-02-17"

    def test_validate_valid_range(self):
        assert self.processor.validate_time_range("2026-03-01", "2026-03-09") is True

    def test_validate_inverted_range(self):
        assert self.processor.validate_time_range("2026-03-09", "2026-03-01") is False

    def test_validate_future_range(self):
        assert self.processor.validate_time_range("2027-01-01", "2027-01-09") is False

    def test_validate_full_year_range(self):
        assert self.processor.validate_time_range("2026-01-01", "2026-03-09") is True

    def test_default_time_range(self):
        result = self.processor.get_default_time_range()
        assert result["start_date"] == "2026-02-08"
        assert result["end_date"] == "2026-03-10"

    def test_last_month_march_31_does_not_crash(self):
        processor = TimeProcessor(now=datetime(2026, 3, 31))
        result = processor.process_time_params({"end": "last_month"})
        assert result["end_date"] == "2026-02-28"

    def test_validate_valid_range_ten_years_ago(self):
        assert self.processor.validate_time_range("2016-03-15", "2016-03-16") is True

    def test_validate_range_beyond_ten_years(self):
        assert self.processor.validate_time_range("2015-03-15", "2016-03-15") is False

    def test_validate_today_is_valid(self):
        assert self.processor.validate_time_range("2026-03-10", "2026-03-10") is True

    def test_validate_future_date_same_tomorrow_invalid(self):
        assert self.processor.validate_time_range("2026-03-11", "2026-03-11") is False

    def test_validate_invalid_date_format(self):
        assert self.processor.validate_time_range("not-a-date", "2026-03-10") is False
