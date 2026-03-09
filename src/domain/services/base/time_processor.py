"""
Time Processor

This module contains utilities for processing and normalizing time parameters
across different services. It centralizes time-related logic to avoid duplication.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class TimeProcessor:
    """Centralized time processing for all services."""
    
    @staticmethod
    def process_time_params(parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize time parameters from parsed query.
        
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
        
        # Determine time range
        if start and end:
            # User provided explicit start and end dates
            result["start_date"] = start
            result["end_date"] = end
        else:
            # Calculate based on time parameters
            end_date = datetime.now()
            start_date = end_date
            
            if days:
                start_date = end_date - timedelta(days=days)
            elif weeks:
                start_date = end_date - timedelta(weeks=weeks)
            elif months:
                # Approximate month calculation
                start_date = end_date.replace(
                    day=1,
                    month=end_date.month - months + 1 if end_date.month > months else 12 - (months - end_date.month) + 1,
                    year=end_date.year - 1 if end_date.month <= months else end_date.year
                )
            elif years:
                start_date = end_date.replace(year=end_date.year - years)
            else:
                # Default to 30 days
                start_date = end_date - timedelta(days=30)
            
            result["start_date"] = start_date.strftime("%Y-%m-%d")
            result["end_date"] = end_date.strftime("%Y-%m-%d")
        
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