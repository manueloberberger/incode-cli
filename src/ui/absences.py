from datetime import datetime, timedelta
from typing import Any

from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner

from src.config import console, BANNER
from src.utils import clear_screen, wait_for_return, get_holidays

def show_absences(incode: Any) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print()
    with Live(Align.center(Spinner("dots", text=" Lade Abwesenheiten ...")), console=console, transient=True):
        # Try the dedicated endpoint first (this was the v1.7 behavior)
        absences = incode.load_absences()
        
        # Fallback to duties only if absolutely nothing found in dedicated absences
        if not absences:
             absences = incode.load_future_duties(filter_mode='only_absences')

    if not absences: 
        console.print(Align.center(f"\n[info]Keine geplanten Abwesenheiten gefunden.[/info]"))
        wait_for_return()
        return

    table = Table(title="🌴  Meine Abwesenheiten", header_style="header", expand=False, box=None, padding=(0, 1), show_header=True)
    table.add_column("Datum", style="info")
    table.add_column("Art", style="warning")
    table.add_column("Dauer", style="dim")
    
    total_vacation_days = 0
    weekday_map = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    for a in absences:
        try:
            b_raw = datetime.strptime(a['begin'], '%Y-%m-%dT%H:%M:%S')
            e_raw = datetime.strptime(a['end'], '%Y-%m-%dT%H:%M:%S')
            reason = a.get('duty_type', '')
            
            # 1. Adjust Start Date (Heuristic: Starts after 20:00 are logically the next day due to TZ/System quirks)
            b = b_raw
            if b_raw.hour >= 20:
                b = b_raw + timedelta(days=1)
                b = b.replace(hour=0, minute=0, second=0)

            # 2. Adjust End Date (00:00 counts as end of previous day)
            e = e_raw
            if e_raw.hour == 0 and e_raw.minute == 0 and e_raw.second == 0:
                e = e_raw - timedelta(seconds=1)
            
            # Duration logic
            total_seconds = int((e_raw - b_raw).total_seconds())
            days_diff = (e.date() - b.date()).days + 1
            
            dur_str = ""
            # Check if it spans almost a full day or multiple days
            if "urlaub" in reason.lower() or "abwesend" in reason.lower() or "sonderabwesenheit" in reason.lower() or "frei" in reason.lower() or total_seconds >= 86000:
                dur_str = "1 Tag" if days_diff == 1 else f"{days_diff} Tage"
            else:
                h = total_seconds / 3600
                dur_str = f"{int(h)} Std." if h == int(h) else f"{h:g} Std."
            
            # Add to summary if it is explicitly "Urlaub"
            if "urlaub" in reason.lower():
                net_days = 0
                curr = b.date()
                end_d = e.date()
                holidays = get_holidays(curr.year)
                if end_d.year != curr.year: holidays.extend(get_holidays(end_d.year))
                
                while curr <= end_d:
                    if curr.weekday() != 6 and curr not in holidays: net_days += 1
                    curr += timedelta(days=1)
                total_vacation_days += net_days

            wd_start = weekday_map[b.weekday()]
            date_str = f"{wd_start} {b.strftime('%d.%m.%Y')}"
            if e.date() > b.date():
                 wd_end = weekday_map[e.weekday()]
                 date_str = f"{wd_start} {b.strftime('%d.%m.')} - {wd_end} {e.strftime('%d.%m.%Y')}"

            table.add_row(date_str, reason, dur_str)
        except Exception: pass
        
    console.print(Align.center(table))
    
    if total_vacation_days > 0:
        console.print(Align.center(f"\n[bold green]Gesamtanspruch Urlaub: {total_vacation_days} Tage[/bold green]"))

    wait_for_return()
