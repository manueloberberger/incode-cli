"""
iCalendar export functionality for incode-cli.

This module provides functions to export duty schedules to iCalendar (.ics) format,
which can be imported into calendar applications like Google Calendar, Outlook, etc.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dataclasses import asdict
from icalendar import Calendar, Event, vText
from src.config import console
from src.utils import parse_iso_datetime, duty_identity

from typing import Dict, Any, Union, Sequence, Optional
from src.models import Duty


def _calendar_date(value: Any) -> Optional[datetime]:
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parse_iso_datetime(value)


def export_to_ics(duties: Sequence[Union[Dict[str, Any], Duty]], filename: str = "dienstplan.ics") -> bool:
    """
    Export duties to iCalendar (.ics) file format.
    
    Creates a standard iCalendar file that can be imported into most calendar
    applications. Each duty becomes a calendar event with time, location,
    and crew information.
    
    Args:
        duties: List of duties (as Dicts or Duty objects).
        filename: Output filename (default: 'dienstplan.ics').
        
    Returns:
        True if export was successful, False otherwise.
        
    Example:
        >>> duties = [{'begin': ...}]
        >>> export_to_ics(duties, 'my_duties.ics')
        True
    """
    cal = Calendar()
    cal.add('prodid', '-//RedCrossIncodeChecker//DE')
    cal.add('version', '2.0')

    created_at = datetime.now(timezone.utc)
    exported = set()
    count = 0

    for item in duties:
        try:
            # Support both Dicts and Dataclasses (Duty objects)
            d: Dict[str, Any] = asdict(item) if isinstance(item, Duty) else item
            dt_start = _calendar_date(d.get('begin'))
            dt_end = _calendar_date(d.get('end'))

            if d.get("is_cancelled") or not dt_start or not dt_end or dt_end <= dt_start:
                continue

            event = Event()
            
            # Build summary from vehicle and duty type
            vehicle = d.get('vehicle') or "Dienst"
            dtype = d.get('duty_type', '')
            summary = vehicle
            if dtype and dtype != vehicle:
                summary += f" ({dtype})"
            event.add('summary', summary)

            # Add date/time properties
            event.add('dtstart', dt_start.replace(tzinfo=ZoneInfo('Europe/Vienna')) if dt_start.tzinfo is None else dt_start)
            event.add('dtend', dt_end.replace(tzinfo=ZoneInfo('Europe/Vienna')) if dt_end.tzinfo is None else dt_end)
            event.add('dtstamp', created_at)

            uid = duty_identity(d) + "@incode-cli"
            if uid in exported:
                continue
            exported.add(uid)
            event.add('uid', uid)
            event.add('last-modified', created_at)

            # Build description from location and crew
            desc_lines = []
            if d.get('location'):
                event.add('location', vText(d['location']))
                desc_lines.append(f"Ort: {d['location']}")
            
            crew = d.get('crew', [])
            if crew:
                c_str = ", ".join(crew) if isinstance(crew, list) else str(crew)
                desc_lines.append(f"Crew: {c_str}")

            if desc_lines:
                event.add('description', "\n".join(desc_lines))

            cal.add_component(event)
            count += 1
            
        except Exception as e:
            console.print(f"[warning]Fehler beim Exportieren eines Events (iCal): {e}[/warning]")

    try:
        with open(filename, 'wb') as f:
            f.write(cal.to_ical())
        console.print(f"[success]iCal-Datei mit {count} Einträgen gespeichert als: {filename}[/success]")
        return True
    except Exception as e:
        console.print(f"[error]Fehler beim Speichern der ICS Datei: {e}[/error]")
        return False