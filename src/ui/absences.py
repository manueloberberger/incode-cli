from datetime import datetime, timedelta
from typing import Any

from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner

from src.config import console, BANNER
from src.utils import clear_screen, wait_for_return, get_holidays, get_key, KEY_ENTER, KEY_ESC

def show_absences(incode: Any) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    with Live(Align.center(Spinner("dots", text=" Lade Abwesenheiten ...")), console=console, transient=True):
        # Try the dedicated endpoint first (this was the v1.7 behavior)
        absences = incode.load_absences()
        
        # Fallback to duties only if absolutely nothing found in dedicated absences
        if not absences:
             absences = incode.load_future_duties(filter_mode='only_absences')

        # NEW: Fetch Live Balance (Saldo)
        user_balance = None
        try:
             # Strategy 1: Search by Username
             candidates = []
             if incode.username:
                 candidates = incode.search_staff_contact(incode.username)
             
             # Strategy 2: Search by Real Name (from DB or Discovered)
             search_name = incode.discovered_name
             
             if not search_name and incode.username:
                 # Try loading from DB config
                 from src.config import load_credentials
                 creds = load_credentials()
                 for u in creds.get('users', []):
                     if str(u.get('username')) == str(incode.username):
                         search_name = u.get('real_name')
                         break
             
             if not candidates and search_name:
                 candidates = incode.search_staff_contact(search_name)

             # Pick best match
             if candidates:
                 # If multiple, try to find one that matches username in PNR or Name
                 user_balance = candidates[0] # Default to first
                 for c in candidates:
                     pnr = str(c.get('personalnummer', ''))
                     name = str(c.get('_display_name', ''))
                     # Exact PNR match with username (rare but perfect)
                     if pnr and incode.username and pnr == incode.username:
                         user_balance = c
                         break
                     # If we searched by name, exact name match is good
                     if incode.discovered_name and incode.discovered_name.lower() in name.lower():
                         user_balance = c
                         # Don't break yet, look for better PNR match potentially? no, name is good enough usually.
        except Exception:
            pass  # Skip balance fetch errors

    if not absences and not user_balance: 
        console.print(Align.center(f"\n[info]Keine geplanten Abwesenheiten gefunden.[/info]"))
        wait_for_return()
        return

    # --- RENDER BALANCE PANEL ---
    if user_balance:
        from rich.panel import Panel
        saldo_u = user_balance.get('saldo_urlaub')
        saldo_za = user_balance.get('saldo_za')
        
        if saldo_u or saldo_za:
            try:
                u_val = float(str(saldo_u or 0).replace(',', '.'))
                u_color = "green" if u_val > 0 else "red"
            except (ValueError, AttributeError):
                u_color = "white"
            
            try:
                za_val = float(str(saldo_za or 0).replace(',', '.'))
                za_color = "green" if za_val > 0 else "red"
            except (ValueError, AttributeError):
                za_color = "white"

            # Use a single centered line for robustness against width issues
            # Format: Resturlaub: 38 Tage   •   Zeitausgleich: 0.02h
            
            text = f"[bold]Resturlaub (Saldo):[/bold] [{u_color}]{saldo_u or '0'} Tage[/{u_color}]   [dim]•[/dim]   [bold]Zeitausgleich:[/bold] [{za_color}]{saldo_za or '0'}h[/{za_color}]"
            
            console.print(Align.center(Panel(Align.center(text), title="Aktueller Anspruch (Live)", border_style="yellow", expand=False)))
            console.print() 

    # Removed extra top spacer based on feedback
    # Title separate to allow spacing below it
    console.print(Align.center("🌴  Meine Abwesenheiten"))
    console.print()
    
    table = Table(header_style="header", expand=False, box=None, padding=(0, 1), show_header=True)
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
        except (ValueError, KeyError):
            pass  # Skip malformed absence entries
        
    console.print(Align.center(table))
    
    if total_vacation_days > 0:
        console.print(Align.center(f"\n[dim]Geplanter Urlaub (in dieser Liste): {total_vacation_days} Tage[/dim]"))

    console.print(Align.center("\n[dim]Drücke 'p' für PDF, 't' für Telegram oder ENTER zum Beenden ...[/dim]"))

    while True:
        k = get_key()
        if not k: continue
        
        if k.lower() == 'p':
            pdf_file = "abwesenheiten.pdf"
            with Live(Align.center(Spinner("dots", text="Erstelle PDF ...")), console=console, transient=True):
                from src.pdf import export_absences_to_pdf
                success = export_absences_to_pdf(absences, pdf_file)
            
            if success:
                console.print(Align.center(f"\n[success]PDF erfolgreich gespeichert: {pdf_file}[/success]"))
                console.print(Align.center("[dim](Datei liegt im Programm-Ordner)[/dim]"))
            else:
                console.print(Align.center("\n[error]Fehler beim Speichern des PDF.[/error]"))
        
        elif k.lower() == 't':
            pdf_file = "abwesenheiten.pdf"
            with Live(Align.center(Spinner("dots", text="Erstelle PDF & Sende an Telegram ...")), console=console, transient=True):
                from src.pdf import export_absences_to_pdf
                from src.ui.components import send_pdf_via_bot
                
                if export_absences_to_pdf(absences, pdf_file):
                    sent = send_pdf_via_bot(incode, pdf_file, caption="🌴 Meine Abwesenheiten")
                    
                    # Cleanup after sending
                    import os
                    if os.path.exists(pdf_file):
                        os.remove(pdf_file)
                        
                    if sent:
                         console.print(Align.center(f"\n[success]Erfolgreich an Telegram gesendet![/success]"))
                    else:
                         console.print(Align.center(f"\n[error]Fehler beim Senden. Bot konfiguriert?[/error]"))

        elif k == KEY_ENTER or (k and k.lower() == 'q') or k == KEY_ESC:
            return
