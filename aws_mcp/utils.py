"""Utility functions for date handling and validation."""

from datetime import date, datetime, timedelta
from typing import Tuple


def iso_date(d: date) -> str:
    """Convert date to ISO format string (YYYY-MM-DD)."""
    return d.strftime("%Y-%m-%d")


def validate_date(date_str: str) -> str:
    """Validate date string format (YYYY-MM-DD).
    
    Args:
        date_str: Date string to validate
        
    Returns:
        The validated date string
        
    Raises:
        ValueError: If date format is invalid
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def get_default_date_range(granularity: str) -> Tuple[str, str]:
    """Generate default start and end dates based on granularity.
    
    Args:
        granularity: Time granularity - DAILY or MONTHLY
        
    Returns:
        Tuple of (start_date, end_date) as ISO strings
    """
    today = date.today()
    
    if granularity == "DAILY":
        start = today - timedelta(days=30)
        end = today
    else:  # MONTHLY
        start = today.replace(day=1)
        end = today
        
    return iso_date(start), iso_date(end)


def get_default_lookback_range(days: int = 30) -> Tuple[str, str]:
    """Get a default date range looking back N days from today.
    
    Args:
        days: Number of days to look back
        
    Returns:
        Tuple of (start_date, end_date) as ISO strings
    """
    today = date.today()
    start = today - timedelta(days=days)
    return iso_date(start), iso_date(today)
