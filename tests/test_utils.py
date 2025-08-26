"""Tests for AWS Cost Explorer utilities."""

import pytest
from datetime import date, timedelta

from aws_mcp.utils import iso_date, validate_date, get_default_date_range, get_default_lookback_range


class TestUtils:
    """Test cases for utility functions."""
    
    def test_iso_date(self):
        """Test ISO date formatting."""
        test_date = date(2023, 12, 25)
        assert iso_date(test_date) == "2023-12-25"
    
    def test_validate_date_valid(self):
        """Test date validation with valid date."""
        valid_date = "2023-12-25"
        assert validate_date(valid_date) == valid_date
    
    def test_validate_date_invalid(self):
        """Test date validation with invalid date."""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date("invalid-date")
        
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date("2023-13-32")
    
    def test_get_default_date_range_daily(self):
        """Test default date range for daily granularity."""
        start, end = get_default_date_range("DAILY")
        
        # Parse the dates back
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        
        # Should be about 30 days difference
        diff = (end_date - start_date).days
        assert diff == 30
        assert end_date == date.today()
    
    def test_get_default_date_range_monthly(self):
        """Test default date range for monthly granularity."""
        start, end = get_default_date_range("MONTHLY")
        
        # Parse the dates back
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        
        # Start should be first day of current month
        today = date.today()
        expected_start = today.replace(day=1)
        
        assert start_date == expected_start
        assert end_date == today
    
    def test_get_default_lookback_range(self):
        """Test default lookback range."""
        start, end = get_default_lookback_range(7)
        
        # Parse the dates back
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        
        # Should be 7 days difference
        diff = (end_date - start_date).days
        assert diff == 7
        assert end_date == date.today()
