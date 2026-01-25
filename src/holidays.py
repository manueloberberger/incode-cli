"""
Holiday calculation module for incode-cli.
Contains Austrian public holiday calculations including Easter-based holidays.
"""
from datetime import date, datetime, timedelta
from typing import List


def get_holidays(year: int) -> List[date]:
    """Returns a list of Austrian holidays for the given year."""
    # Fixed holidays
    holidays = [
        datetime(year, 1, 1).date(),   # Neujahr
        datetime(year, 1, 6).date(),   # Heilige Drei Könige
        datetime(year, 5, 1).date(),   # Staatsfeiertag
        datetime(year, 8, 15).date(),  # Mariä Himmelfahrt
        datetime(year, 10, 10).date(), # Tag der Volksabstimmung (Kärnten)
        datetime(year, 10, 26).date(), # Nationalfeiertag
        datetime(year, 11, 1).date(),  # Allerheiligen
        datetime(year, 12, 8).date(),  # Mariä Empfängnis
        datetime(year, 12, 24).date(), # Heiligabend
        datetime(year, 12, 25).date(), # Christtag
        datetime(year, 12, 26).date(), # Stefanitag
        datetime(year, 12, 31).date()  # Silvester
    ]
    
    # Variable (Easter based) - Computus algorithm
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    dy = ((h + l - 7 * m + 114) % 31) + 1
    easter = datetime(year, mo, dy).date()
    
    # Easter-based holidays:
    # Ostersonntag (0), Ostermontag (+1), Himmelfahrt (+39), 
    # Pfingstsonntag (+49), Pfingstmontag (+50), Fronleichnam (+60)
    holidays.append(easter)                       # Easter Sunday
    holidays.append(easter + timedelta(days=1))   # Easter Monday

    holidays.append(easter + timedelta(days=39))  # Ascension
    holidays.append(easter + timedelta(days=49))  # Whit Sunday
    holidays.append(easter + timedelta(days=50))  # Whit Monday
    holidays.append(easter + timedelta(days=60))  # Corpus Christi
    
    return holidays
