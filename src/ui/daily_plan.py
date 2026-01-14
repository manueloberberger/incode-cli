from datetime import datetime, date
from typing import Optional, List, Any

from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner

from src.config import console, BANNER
from src.utils import clear_screen, wait_for_return, flush_input, get_key
from src.pdf import export_to_pdf
from src.ical import export_to_ics
from src.ui.components import send_pdf_via_bot

def show_daily_plan(incode: Any, date: Optional[datetime] = None, is_live: bool = False, override_plan: Optional[List[Any]] = None) -> Optional[List[Any]]:
    if not is_live:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print()

    if not date: date = datetime.now()
    
    plan = None
    if override_plan is not None:
        plan = override_plan
    else:
        if not is_live:
            with Live(Align.center(Spinner("dots", text=" Lade Gesamten Tagesplan ...")), console=console, transient=True):
                plan = incode.load_daily_plan(date)
        else:
            plan = incode.load_daily_plan(date)
        
    if not plan:
        if not is_live: 
            console.print(Align.center(f"\n[info]Keine Plan für {date.strftime('%d.%m.%Y')}.[/info]"))
            wait_for_return()
        return None
    
    if not is_live:
        console.print(Align.center(f"[bold header]TAGESPLAN {date.strftime('%d.%m.%Y')}[/bold header]"))
        console.print()
        
    table = Table(header_style="header", expand=False, box=None, padding=(0, 1))
    table.add_column("Zeit", style="info"); table.add_column("Fzg", style="success"); table.add_column("Besatzung")
    
    # Prepare data for export logic later
    export_duties = []

    for p in plan:
        try:
            b, e = p["begin"], p["end"]
            if b and e:
                h = (e - b).total_seconds() / 3600
                cl = []
                for r in ["FAHRER", "SANITAETER1", "SANITAETER2"]:
                    if r in p["crew"]:
                        cl.append(p['crew'][r])
                
                # Add to table
                table.add_row(f"{b.strftime('%H:%M')}-{e.strftime('%H:%M')} ({h:g}h) ", p['vehicle'], ", ".join(cl))

                # Add to export list
                export_duties.append({
                    'begin': b.strftime('%Y-%m-%dT%H:%M:%S'),
                    'end': e.strftime('%Y-%m-%dT%H:%M:%S'),
                    'location': "", 
                    'vehicle': p['vehicle'],
                    'duty_type': "", 
                    'crew': cl
                })
        except Exception: pass
        
    if is_live:
        clear_screen()
        console.print(Align.center(BANNER))
        # print('\a') # Bell sound removed
        console.print(Align.center(f"[live]● LIVE MODUS[/live]  [dim]Letztes Update: {datetime.now().strftime('%H:%M:%S')}[/dim]"))
        console.print() # Added blank line
        if override_plan is not None:
             # If we are in live mode and updated, maybe show a small indicator
             pass
        console.print(Align.center(table))
        console.print()
        return plan
    else: 
        console.print(Align.center(table))
        console.print()
        
        opt_str = "'p' für PDF, 'c' für Kalender (iCal), 't' für PDF & Telegram"
        console.print(Align.center(f"\n[dim]Drücke {opt_str}, oder eine beliebige andere Taste ...[/dim]"))
        
        flush_input()
        while True:
            k = get_key()
            if k:
                k = k.lower()
                date_iso = date.strftime('%Y-%m-%d')
                time_iso = datetime.now().strftime('%H-%M')
                
                if k == 'p' or k == 't':
                    fn = f"Tagesplan_{date_iso}_{time_iso}.pdf"
                    if export_to_pdf(export_duties, fn):
                        if k == 't':
                            msg = f"Tagesplan Export vom {date.strftime('%d.%m.%Y')}"
                            if send_pdf_via_bot(incode, fn, msg):
                                console.print("[success]PDF erfolgreich per Telegram gesendet !!![/success]")
                    wait_for_return()
                    break
                elif k == 'c':
                    fn = f"Tagesplan_{date_iso}_{time_iso}.ics"
                    export_to_ics(export_duties, fn)
                    wait_for_return()
                    break
                else:
                    break
    return plan
