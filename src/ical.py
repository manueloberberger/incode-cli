from datetime import datetime
from src.config import console

def format_dt(iso_str):
    """
    Converts ISO format YYYY-MM-DDTHH:MM:SS to iCal format YYYYMMDDTHHMMSS
    """
    if not iso_str: return ""
    return iso_str.replace("-", "").replace(":", "")

def export_to_ics(duties, filename="dienstplan.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//RedCrossIncodeChecker//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]

    now_str = datetime.now().strftime('%Y%m%dT%H%M%S')

    for d in duties:
        try:
            start = format_dt(d.get('begin'))
            end = format_dt(d.get('end'))
            if not start or not end: continue

            # Create a unique UID based on start time and vehicle/type
            veh = d.get('vehicle', '').replace(" ", "_")
            uid = f"{start}-{veh}-{now_str}@incodechecker"
            
            # Construct Summary
            vehicle = d.get('vehicle') or "Dienst"
            dtype = d.get('duty_type', '')
            
            summary = vehicle
            if dtype and dtype != vehicle:
                summary += f" ({dtype})"
            
            # Construct Description
            desc = []
            if d.get('location'): 
                desc.append(f"Ort: {d['location']}")
            
            crew = d.get('crew', [])
            if crew:
                # If crew is a list, join it. If it's a string, just use it.
                c_str = ", ".join(crew) if isinstance(crew, list) else str(crew)
                desc.append(f"Crew: {c_str}")
            
            lines.append("BEGIN:VEVENT")
            lines.append(f"DTSTART:{start}")
            lines.append(f"DTEND:{end}")
            lines.append(f"DTSTAMP:{now_str}")
            lines.append(f"UID:{uid}")
            lines.append(f"SUMMARY:{summary}")
            if desc:
                # Escape newlines for iCal
                desc_text = "\\n".join(desc)
                lines.append(f"DESCRIPTION:{desc_text}")
            lines.append("END:VEVENT")
        except Exception as e:
            console.print(f"[warning]Fehler beim Exportieren eines Events (iCal): {e}[/warning]")

    lines.append("END:VCALENDAR")

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        console.print(f"[success]iCal-Datei gespeichert als: {filename}[/success]")
        return True
    except Exception as e:
        console.print(f"[error]Fehler beim Speichern der ICS Datei: {e}[/error]")
        return False
