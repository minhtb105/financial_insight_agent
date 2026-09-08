import calendar
import re
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field, field_validator, model_validator

TICKER_PATTERN = re.compile(r"^[A-Z0-9]{2,8}$")

_SPECIAL_ENDS = frozenset({"yesterday", "today", "last_week", "last_month"})
_DEFAULT_LOOKBACK_DAYS = 30


def validate_ticker_list(tickers: list[str]) -> list[str]:
    """Validate and normalize a list of stock tickers."""
    if not tickers:
        raise ValueError("At least one ticker is required")
    result = []
    for ticker in tickers:
        if not isinstance(ticker, str) or not TICKER_PATTERN.match(ticker.upper()):
            raise ValueError(f"Invalid ticker: {ticker}")
        result.append(ticker.upper())
    return result


class TimeRange(BaseModel):
    start: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end: str | None = Field(None, description="End date (YYYY-MM-DD)")
    days: int | None = Field(None, description="Number of days")
    weeks: int | None = Field(None, description="Number of weeks")
    months: int | None = Field(None, description="Number of months")
    years: int | None = Field(None, description="Number of years")

    @field_validator("days", "weeks", "months", "years")
    def validate_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Time parameters must be positive")
        return v

    @model_validator(mode="after")
    def validate_not_ambiguous(self):
        has_relative = any(x is not None for x in (self.days, self.weeks, self.months, self.years))
        if self.start is not None and has_relative:
            raise ValueError(
                "Cannot combine 'start' with relative time parameters (days/weeks/months/years)"
            )
        if self.end is not None and has_relative:
            raise ValueError(
                "Cannot combine 'end' with relative time parameters (days/weeks/months/years)"
            )
        return self

    @staticmethod
    def _resolve_special_end(end: str, now: datetime | None = None) -> str:
        if not end or end not in _SPECIAL_ENDS:
            return end
        now = now or datetime.now(timezone.utc)
        if end == "yesterday":
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        if end == "today":
            return now.strftime("%Y-%m-%d")
        if end == "last_week":
            return (now - timedelta(days=7)).strftime("%Y-%m-%d")
        if end == "last_month":
            if now.month == 1:
                last = now.replace(year=now.year - 1, month=12)
            else:
                last = now.replace(month=now.month - 1, day=1)
            month_days = calendar.monthrange(last.year, last.month)[1]
            last = last.replace(day=min(now.day, month_days))
            return last.strftime("%Y-%m-%d")
        return end

    @staticmethod
    def subtract_months(date: datetime, months: int) -> datetime:
        total_months = date.year * 12 + date.month - 1 - months
        year = total_months // 12
        month = total_months % 12 + 1
        month_days = calendar.monthrange(year, month)[1]
        try:
            return date.replace(year=year, month=month, day=min(date.day, month_days))
        except ValueError:
            return date.replace(year=year, month=month, day=month_days)

    def resolve(self, now: datetime | None = None) -> dict[str, str]:
        now = now or datetime.now(timezone.utc)
        end = self._resolve_special_end(self.end, now)
        if self.start and end:
            return {"start": self.start, "end": end}
        if self.start and not end:
            return {"start": self.start, "end": now.strftime("%Y-%m-%d")}
        if end and not self.start:
            end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if self.days or self.weeks or self.months or self.years:
                start_dt = end_dt
                if self.years:
                    try:
                        start_dt = start_dt.replace(year=start_dt.year - self.years)
                    except ValueError:
                        start_dt = start_dt.replace(year=start_dt.year - self.years, day=28)
                if self.months:
                    start_dt = self.subtract_months(start_dt, self.months)
                if self.weeks:
                    start_dt -= timedelta(weeks=self.weeks)
                if self.days:
                    start_dt -= timedelta(days=self.days)
            else:
                start_dt = end_dt - timedelta(days=_DEFAULT_LOOKBACK_DAYS)
            return {"start": start_dt.strftime("%Y-%m-%d"), "end": end}
        end_date = now
        start_date = end_date
        if self.days:
            start_date = end_date - timedelta(days=self.days)
        elif self.weeks:
            start_date = end_date - timedelta(weeks=self.weeks)
        elif self.months:
            start_date = self.subtract_months(end_date, self.months)
        elif self.years:
            try:
                start_date = end_date.replace(year=end_date.year - self.years)
            except ValueError:
                start_date = end_date.replace(year=end_date.year - self.years, day=28)
        return {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        }
