"""
Holiday calculation module for incode-cli.
Contains Austrian public holiday calculations including Easter-based holidays.
"""
from datetime import date, datetime, timedelta
from typing import List


def get_holidays(year: int) -> List[date]:
    """
    Calculate all Austrian public holidays for a given year.

    This function returns both fixed holidays (same date every year)
    and moveable holidays based on Easter Sunday.

    Args:
        year: The year to calculate holidays for.

    Returns:
        List of date objects representing Austrian public holidays.

    Note:
        Includes Carinthian regional holiday (Tag der Volksabstimmung).
        Also includes common non-working days (Heiligabend, Silvester).
    """
    # Fixed holidays (same date every year)
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

    # ============================================================
    # COMPUTUS ALGORITHM - Calculate Easter Sunday
    # ============================================================
    # This is the "Anonymous Gregorian Algorithm" (Meeus/Jones/Butcher),
    # a variant of the Computus algorithm used to calculate the date
    # of Easter Sunday in the Gregorian calendar.
    #
    # The algorithm determines Easter as the first Sunday after the
    # first ecclesiastical full moon on or after March 21 (vernal equinox).
    #
    # Variables:
    #   a = year's position in 19-year Metonic cycle
    #   b, c = century and year within century
    #   d, e = leap year corrections for century
    #   f, g = corrections for lunar orbit irregularities
    #   h = days from March 21 to full moon (0-29)
    #   i, k = leap year corrections for year
    #   l = days from full moon to next Sunday (0-6)
    #   m = correction for leap months
    #   mo, dy = resulting month and day of Easter
    # ============================================================
    a = year % 19                           # Metonic cycle position
    b = year // 100                         # Century
    c = year % 100                          # Year within century
    d = b // 4                              # Leap centuries
    e = b % 4                               # Non-leap century correction
    f = (b + 8) // 25                       # Lunar orbit correction
    g = (b - f + 1) // 3                    # Additional correction
    h = (19 * a + b - d - g + 15) % 30      # Full moon calculation
    i, k = c // 4, c % 4                    # Leap year within century
    l = (32 + 2 * e + 2 * i - h - k) % 7    # Days to Sunday
    m = (a + 11 * h + 22 * l) // 451        # Leap month correction
    mo = (h + l - 7 * m + 114) // 31        # Easter month (3=March, 4=April)
    dy = ((h + l - 7 * m + 114) % 31) + 1   # Easter day
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
