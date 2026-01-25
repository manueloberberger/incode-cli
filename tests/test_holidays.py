"""
Tests for the holiday calculations in src/holidays.py
"""
import pytest
import sys
import os
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.holidays import get_holidays


class TestFixedHolidays:
    """Tests for fixed (non-Easter-based) holidays."""
    
    def test_neujahr(self):
        """Test New Year's Day."""
        for year in [2024, 2025, 2026]:
            holidays = get_holidays(year)
            assert date(year, 1, 1) in holidays

    def test_heilige_drei_koenige(self):
        """Test Epiphany (Jan 6)."""
        holidays = get_holidays(2026)
        assert date(2026, 1, 6) in holidays

    def test_staatsfeiertag(self):
        """Test Labour Day (May 1)."""
        holidays = get_holidays(2026)
        assert date(2026, 5, 1) in holidays

    def test_maria_himmelfahrt(self):
        """Test Assumption of Mary (Aug 15)."""
        holidays = get_holidays(2026)
        assert date(2026, 8, 15) in holidays

    def test_nationalfeiertag(self):
        """Test Austrian National Day (Oct 26)."""
        holidays = get_holidays(2026)
        assert date(2026, 10, 26) in holidays

    def test_allerheiligen(self):
        """Test All Saints' Day (Nov 1)."""
        holidays = get_holidays(2026)
        assert date(2026, 11, 1) in holidays

    def test_maria_empfaengnis(self):
        """Test Immaculate Conception (Dec 8)."""
        holidays = get_holidays(2026)
        assert date(2026, 12, 8) in holidays

    def test_weihnachten(self):
        """Test Christmas holidays."""
        holidays = get_holidays(2026)
        assert date(2026, 12, 24) in holidays  # Heiligabend
        assert date(2026, 12, 25) in holidays  # Christtag
        assert date(2026, 12, 26) in holidays  # Stefanitag

    def test_silvester(self):
        """Test New Year's Eve."""
        holidays = get_holidays(2026)
        assert date(2026, 12, 31) in holidays

    def test_tag_der_volksabstimmung(self):
        """Test Carinthian Plebiscite Day (Oct 10)."""
        holidays = get_holidays(2026)
        assert date(2026, 10, 10) in holidays


class TestEasterHolidays:
    """Tests for Easter-based holidays."""
    
    # Known Easter dates for verification
    # 2024: March 31, 2025: April 20, 2026: April 5, 2027: March 28
    
    def test_easter_2024(self):
        """Test Easter 2024 (March 31)."""
        holidays = get_holidays(2024)
        easter_sunday = date(2024, 3, 31)
        easter_monday = date(2024, 4, 1)
        
        assert easter_sunday in holidays
        assert easter_monday in holidays

    def test_easter_2025(self):
        """Test Easter 2025 (April 20)."""
        holidays = get_holidays(2025)
        easter_sunday = date(2025, 4, 20)
        easter_monday = date(2025, 4, 21)
        
        assert easter_sunday in holidays
        assert easter_monday in holidays

    def test_easter_2026(self):
        """Test Easter 2026 (April 5)."""
        holidays = get_holidays(2026)
        easter_sunday = date(2026, 4, 5)
        easter_monday = date(2026, 4, 6)
        
        assert easter_sunday in holidays
        assert easter_monday in holidays

    def test_karfreitag_2026(self):
        """Test Good Friday 2026 (Easter - 2 days)."""
        holidays = get_holidays(2026)
        # Easter 2026 is April 5, so Good Friday is April 3
        assert date(2026, 4, 3) in holidays

    def test_christi_himmelfahrt_2026(self):
        """Test Ascension Day 2026 (Easter + 39 days)."""
        holidays = get_holidays(2026)
        # Easter 2026 is April 5, so Ascension is May 14
        assert date(2026, 5, 14) in holidays

    def test_pfingsten_2026(self):
        """Test Pentecost 2026 (Easter + 49/50 days)."""
        holidays = get_holidays(2026)
        # Easter 2026 is April 5
        # Pfingstsonntag: May 24, Pfingstmontag: May 25
        assert date(2026, 5, 24) in holidays  # Whit Sunday
        assert date(2026, 5, 25) in holidays  # Whit Monday

    def test_fronleichnam_2026(self):
        """Test Corpus Christi 2026 (Easter + 60 days)."""
        holidays = get_holidays(2026)
        # Easter 2026 is April 5, so Fronleichnam is June 4
        assert date(2026, 6, 4) in holidays


class TestHolidayCount:
    """Tests for total holiday count."""
    
    def test_holiday_count(self):
        """Test that we have the expected number of holidays."""
        holidays = get_holidays(2026)
        
        # 12 fixed + 7 Easter-based = 19 total
        # Fixed: Jan 1, Jan 6, May 1, Aug 15, Oct 10, Oct 26, Nov 1, Dec 8, Dec 24, Dec 25, Dec 26, Dec 31
        # Easter: Easter Sunday, Easter Monday, Good Friday, Ascension, Whit Sunday, Whit Monday, Corpus Christi
        assert len(holidays) == 19

    def test_no_duplicates(self):
        """Test that there are no duplicate holidays."""
        holidays = get_holidays(2026)
        assert len(holidays) == len(set(holidays))


class TestEdgeCases:
    """Edge case tests."""
    
    def test_early_easter(self):
        """Test a year with early Easter (March)."""
        # 2024 has Easter on March 31
        holidays = get_holidays(2024)
        assert date(2024, 3, 31) in holidays

    def test_late_easter(self):
        """Test a year with late Easter (April)."""
        # 2025 has Easter on April 20
        holidays = get_holidays(2025)
        assert date(2025, 4, 20) in holidays

    def test_leap_year(self):
        """Test holiday calculation in a leap year."""
        holidays = get_holidays(2024)  # 2024 is a leap year
        
        # All fixed holidays should still work
        assert date(2024, 1, 1) in holidays
        assert date(2024, 12, 25) in holidays
