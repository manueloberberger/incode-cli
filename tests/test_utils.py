import pytest
import sys
import os
from datetime import date
from io import StringIO
from rich.console import Console

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import get_holidays, unicode_len, prompt_yes_no

def test_get_holidays_fixed():
    """Test fixed holidays for 2026."""
    holidays = get_holidays(2026)
    
    # Check fixed dates
    assert date(2026, 1, 1) in holidays
    assert date(2026, 12, 24) in holidays
    assert date(2026, 10, 26) in holidays
    
def test_get_holidays_easter_2026():
    """Test dynamic easter holidays for 2026."""
    # Easter 2026 is April 5th
    holidays = get_holidays(2026)
    
    easter_sunday = date(2026, 4, 5)
    easter_monday = date(2026, 4, 6)
    
    assert easter_sunday in holidays
    assert easter_monday in holidays
    
    # Ascension (Easter + 39) -> May 14
    assert date(2026, 5, 14) in holidays

def test_unicode_len():
    """Test visual length calculation."""
    assert unicode_len("Hello") == 5
    assert unicode_len("Hello World") == 11
    # String with ANSI codes
    assert unicode_len("\x1b[31mRed\x1b[0m") == 3
    assert unicode_len("[bold]Bold[/bold]") == 17 # [bold] (6) + Bold (4) + [/bold] (7) = 17 
    # Let's verify what `utils.py` actually does. It strips ANSI codes.
    # If the input is just text with rich markup, unicode_len might count the brackets if not rendered.
    # The utils regex: r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])' targets terminal escape codes.

def test_unicode_len_ansi():
    # Simulate a string that would be returned by rich console export or similar if it contained ANSI
    # But usually we use this on input strings.
    pass
