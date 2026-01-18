from datetime import datetime
from icalendar import Calendar, Event, vText
from src.config import console

from typing import List, Dict, Any

def export_to_ics(duties: List[Dict[str, Any]], filename: str = "dienstplan.ics") -> bool:
    cal = Calendar()
    cal.add('prodid', '-//RedCrossIncodeChecker//DE')
    cal.add('version', '2.0')

    created_at = datetime.now()

    count = 0
    for d in duties:
        try:
            # Parse timestamps (Assuming they come as ISO strings from API)
            start_str = d.get('begin')
            end_str = d.get('end')
            
            if not start_str or not end_str:
                continue

            # Convert ISO strings to datetime objects if they aren't already
            if isinstance(start_str, str):
                dt_start = datetime.strptime(start_str[:19], '%Y-%m-%dT%H:%M:%S')
            else:
                dt_start = start_str

            if isinstance(end_str, str):
                dt_end = datetime.strptime(end_str[:19], '%Y-%m-%dT%H:%M:%S')
            else:
                dt_end = end_str

            event = Event()
            
            # Summary
            vehicle = d.get('vehicle') or "Dienst"
            dtype = d.get('duty_type', '')
            summary = vehicle
            if dtype and dtype != vehicle:
                summary += f" ({dtype})"
            event.add('summary', summary)

            # Dates
            event.add('dtstart', dt_start)
            event.add('dtend', dt_end)
            event.add('dtstamp', created_at)

            # Unique ID
            veh_safe = str(vehicle).replace(" ", "_")
            uid = f"{dt_start.strftime('%Y%m%dT%H%M%S')}-{veh_safe}@incodechecker"
            event.add('uid', uid)

            # Description
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