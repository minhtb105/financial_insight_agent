"""
Time Processor

This module contains utilities for processing and normalizing time parameters
across different services. It centralizes time-related logic to avoid duplication.
"""

from datetime import datetime, timedelta
from typing import Dict, Any


class TimeProcessor:
    """Centralized time processing for all services."""
    
    @staticmethod
    def process_time_params(parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize time parameters from parsed query.
        Uses hybrid approach: LLM extraction + rule-based fallback for missing params.
        
        Args:
            parsed_query: Dictionary containing time parameters
            
        Returns:
            Dictionary with normalized time parameters
        """
        result = {}
        
        # Extract time parameters
        start = parsed_query.get("start")
        end = parsed_query.get("end")
        days = parsed_query.get("days")
        weeks = parsed_query.get("weeks")
        months = parsed_query.get("months")
        years = parsed_query.get("years")
        
        # Process special end values
        processed_end = TimeProcessor._process_special_end_value(end)
        
        # Special case: when we have end (special value) + time units but no start
        # Calculate time units from TODAY context, then apply end adjustment
        if not start and processed_end and (days or weeks or months or years):
            now = datetime.now()
            end_date = datetime.strptime(processed_end, "%Y-%m-%d")
            
            # Calculate start_date based on TODAY and time units
            if days:
                start_date = now - timedelta(days=days)
            elif weeks:
                start_date = now - timedelta(weeks=weeks)
            elif months:
                start_date = TimeProcessor._subtract_months(now, months)
            elif years:
                start_date = now.replace(year=now.year - years)
            else:
                start_date = now - timedelta(days=7)
            
            # Ensure start_date <= end_date
            if start_date > end_date:
                start_date = end_date
            
            result["start_date"] = start_date.strftime("%Y-%m-%d")
            result["end_date"] = end_date.strftime("%Y-%m-%d")
        
        # Determine time range
        elif start and processed_end:
            # User provided explicit start and end dates
            result["start_date"] = start
            result["end_date"] = processed_end
        else:
            # Use LLM-extracted params first, then fallback to rule-based
            result = TimeProcessor._fill_missing_time_params(start, processed_end, days, weeks, months, years)
        
        # Add original parameters for reference
        result["original_params"] = {
            "start": start,
            "end": end,
            "days": days,
            "weeks": weeks,
            "months": months,
            "years": years
        }
        
        return result

    @staticmethod
    def _fill_missing_time_params(start: str, end: str, days: int, weeks: int, months: int, years: int) -> Dict[str, Any]:
        """
        Fill missing time parameters using rule-based fallback.
        Handles cases where LLM only returns partial time info.
        """
        result = {}
        end_date = datetime.now()
        
        # If only end is provided (common LLM issue)
        if end and not start:
            end_date = datetime.strptime(end, "%Y-%m-%d")
            start_date = end_date
            
            # Try to infer start from context
            if days:
                start_date = end_date - timedelta(days=days)
            elif weeks:
                start_date = end_date - timedelta(weeks=weeks)
            elif months:
                start_date = TimeProcessor._subtract_months(end_date, months)
            elif years:
                start_date = end_date.replace(year=end_date.year - years)
            else:
                # Default fallback: 7 days before end
                start_date = end_date - timedelta(days=7)
        
        # If only start is provided
        elif start and not end:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.now()
            
            # If start is in future, use start as end and go back 7 days
            if start_date > end_date:
                end_date = start_date
                start_date = end_date - timedelta(days=7)
        
        # If no start/end but has time units
        elif not start and not end:
            if days:
                start_date = end_date - timedelta(days=days)
            elif weeks:
                start_date = end_date - timedelta(weeks=weeks)
            elif months:
                start_date = TimeProcessor._subtract_months(end_date, months)
            elif years:
                start_date = end_date.replace(year=end_date.year - years)
            else:
                # Default to 30 days
                start_date = end_date - timedelta(days=30)
        
        else:
            # Both start and end provided, use as-is
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
        
        result["start_date"] = start_date.strftime("%Y-%m-%d")
        result["end_date"] = end_date.strftime("%Y-%m-%d")
        
        return result

    @staticmethod
    def _subtract_months(date: datetime, months: int) -> datetime:
        """Helper to subtract months from date with proper handling."""
        year = date.year - (months // 12)
        month = date.month - (months % 12)
        
        if month <= 0:
            year -= 1
            month += 12
        
        # Handle month-end dates
        day = min(date.day, 31 if month in [1, 3, 5, 7, 8, 10, 12] else 30 if month in [4, 6, 9, 11] else 28)
        
        return date.replace(year=year, month=month, day=day)
    
    @staticmethod
    def _process_special_end_value(end: str) -> str:
        """Process special end values like 'yesterday', 'today', etc."""
        if not end:
            return end
        
        now = datetime.now()
        
        if end == "yesterday":
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        elif end == "today":
            return now.strftime("%Y-%m-%d")
        elif end == "last_week":
            # Return 7 days before current date
            return (now - timedelta(days=7)).strftime("%Y-%m-%d")
        elif end == "last_month":
            # Return the same day of the previous month
            if now.month == 1:
                last_month = now.replace(year=now.year - 1, month=12)
            else:
                last_month = now.replace(month=now.month - 1)
            
            # Handle month-end dates (e.g., Jan 31 -> Feb 28/29)
            try:
                last_month_date = last_month.replace(day=now.day)
            except ValueError:
                # If the day doesn't exist in the previous month, use the last day of that month
                if last_month.month == 2:
                    # February
                    if (last_month.year % 4 == 0 and last_month.year % 100 != 0) or (last_month.year % 400 == 0):
                        last_month_date = last_month.replace(day=29)  # Leap year
                    else:
                        last_month_date = last_month.replace(day=28)
                elif last_month.month in [4, 6, 9, 11]:
                    last_month_date = last_month.replace(day=30)
                else:
                    last_month_date = last_month.replace(day=31)
            
            return last_month_date.strftime("%Y-%m-%d")
        
        return end
    
    @staticmethod
    def validate_time_range(start_date: str, end_date: str) -> bool:
        """
        Validate that the time range is valid.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            True if time range is valid, False otherwise
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            # End date should be after start date
            if end < start:
                return False
            
            # End date should not be in the future (allowing some flexibility)
            now = datetime.now()
            if end > now + timedelta(days=1):
                return False
            
            # Start date should not be too far in the past (limit to 10 years)
            ten_years_ago = now - timedelta(days=365 * 10)
            if start < ten_years_ago:
                return False
            
            return True
        
        except ValueError:
            return False
    
    @staticmethod
    def get_default_time_range() -> Dict[str, str]:
        """
        Get default time range (last 30 days).
        
        Returns:
            Dictionary with default start and end dates
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }
    
    @staticmethod
    def calculate_business_days(start_date: str, end_date: str) -> int:
        """
        Calculate number of business days in the time range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Number of business days
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            business_days = 0
            current = start
            
            while current <= end:
                # Check if it's a business day (Monday = 0, Sunday = 6)
                if current.weekday() < 5:  # Monday to Friday
                    business_days += 1
                current += timedelta(days=1)
            
            return business_days
        
        except ValueError:
            return 0
    
    @staticmethod
    def format_time_range(start_date: str, end_date: str) -> str:
        """
        Format time range for display purposes.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Formatted time range string
        """
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
        """
        Adjust date to market trading hours.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with market open and close times
        """
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Vietnam market hours: 9:00 AM to 3:00 PM
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
        """
        Get a human-readable description of the time range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Human-readable time description
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Calculate difference
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


def process_service_time_params(service_name: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to process time parameters for a specific service.
    
    Args:
        service_name: Name of the service (for logging/debugging)
        parsed_query: Dictionary containing time parameters
        
    Returns:
        Dictionary with processed time parameters
    """
    time_processor = TimeProcessor()
    processed_time = time_processor.process_time_params(parsed_query)
    
    # Validate the time range
    if not time_processor.validate_time_range(processed_time["start_date"], processed_time["end_date"]):
        # Fall back to default time range
        default_time = time_processor.get_default_time_range()
        processed_time["start_date"] = default_time["start_date"]
        processed_time["end_date"] = default_time["end_date"]
    
    # Add service-specific metadata
    processed_time["service"] = service_name
    processed_time["time_description"] = time_processor.get_relative_time_description(
        processed_time["start_date"], 
        processed_time["end_date"]
    )
    
    return processed_time