import os
import shutil
import subprocess
import time
import sys
import calendar
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Tuple, Optional, Any, Dict
from rich.table import Table
from rich.prompt import Prompt
from rich.live import Live
from rich.console import Group

from src.config import console, BANNER, load_credentials
from src.utils import get_key, wait_for_return, clear_screen, flush_input, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC, KEY_UP_ALT, KEY_DOWN_ALT, KEY_LEFT, KEY_RIGHT, KEY_LEFT_ALT, KEY_RIGHT_ALT
from src.pdf import export_to_pdf
from src.ical import export_to_ics

# Import Bot for internal sending
# Use a lazy import or import inside function to avoid circular dep if needed, 
# but here it should be fine if bot.py imports only config/api.
from src.bot import IncodeBot

def send_pdf_via_bot(incode_instance, file_path: str, caption: str) -> bool:
    """Helper to send a PDF via the built-in bot logic."""
    try:
        # We need a bot instance. It needs an API instance (which we have).
        bot = IncodeBot(incode_instance)
        # Check if configured
        creds = load_credentials()
        if not creds.get("telegram_token") or not creds.get("allowed_user_id"):
            console.print("[yellow]Telegram Bot ist noch nicht konfiguriert.[/yellow]")
            console.print("Bitte starte einmal 'Telegram Bot starten' im Hauptmenü oder 'incode bot'.")
            return False
            
        chat_id = creds["allowed_user_id"]
        success = bot.send_document(chat_id, file_path, caption)
        return success
    except Exception as e:
        console.print(f"[error]Fehler beim Bot-Versand: {e}[/error]")
        return False

def interactive_menu(options: List[Tuple[str, str]], title: str = "HAUPTMENÜ") -> Optional[str]:
    """
    Renders an interactive menu navigated by arrow keys.
    options: list of tuples (Label, ReturnValue)
             e.g. [("Mein Dienstplan", "my_plan"), ("Beenden", "exit")]
    Returns: The ReturnValue of the selected option, or None if ESC is pressed.
    """
    selected_idx = 0
    
    while True:
        clear_screen()
        console.print(BANNER)
        console.print(f"\n[header]{title}[/header]\n")
        
        for idx, (label, _) in enumerate(options):
            if idx == selected_idx:
                console.print(f"[bold green]> {label}[/bold green]")
            else:
                console.print(f"  {label}")
        
        console.print("\n[dim]⬆/⬇ Navigieren • ↵ Auswählen • ESC Zurück/Beenden[/dim]")

        key = get_key()
        
        if key == KEY_UP or key == KEY_UP_ALT:
            selected_idx = (selected_idx - 1) % len(options)
        elif key == KEY_DOWN or key == KEY_DOWN_ALT:
            selected_idx = (selected_idx + 1) % len(options)
        elif key == KEY_ENTER:
            return options[selected_idx][1]
        elif key == KEY_ESC or (key and key.lower() == 'q'):
            return None

def select_date_interactive() -> Optional[datetime]:
    """
    Interactive calendar date selection.
    """
    current_date = datetime.now()
    selected_date = current_date
    
    while True:
        clear_screen()
        console.print(BANNER)
        console.print(f"\n[header]DATUMS-AUSWAHL[/header]")
        
        year, month = selected_date.year, selected_date.month
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]
        
        table = Table(title=f"{month_name} {year}", box=None, padding=(0, 1))
        for day_name in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
            table.add_column(day_name, justify="center", style="dim")
            
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append("")
                else:
                    d_str = str(day)
                    if day == selected_date.day:
                        row.append(f"[black on green]{d_str}[/]")
                    elif day == current_date.day and month == current_date.month and year == current_date.year:
                         row.append(f"[bold blue]{d_str}[/]")
                    else:
                        row.append(d_str)
            table.add_row(*row)
            
        console.print(table)
        console.print("\n[dim]Pfeiltasten zum Navigieren • ↵ Auswählen • ESC Abbrechen[/dim]")
        
        key = get_key()
        
        if not key: continue

        if key == KEY_LEFT or key == KEY_LEFT_ALT:
            selected_date -= timedelta(days=1)
        elif key == KEY_RIGHT or key == KEY_RIGHT_ALT:
            selected_date += timedelta(days=1)
        elif key == KEY_UP or key == KEY_UP_ALT:
            selected_date -= timedelta(weeks=1)
        elif key == KEY_DOWN or key == KEY_DOWN_ALT:
            selected_date += timedelta(weeks=1)
        elif key == KEY_ENTER:
            return selected_date
        elif key == KEY_ESC or key.lower() == 'q':
            return None

from rich.panel import Panel
from rich.columns import Columns
from rich.pretty import Pretty

def show_staff_search(incode: Any) -> None:
    query = Prompt.ask("Name, PNR oder Kürzel eingeben")
    if not query: return
    
    with console.status(f"[bold green]Suche im Verzeichnis nach '{query}'..."):
        results = incode.search_staff_contact(query)
        
    if not results:
        console.print(f"[warning]Nichts gefunden für '{query}'.[/warning]")
        wait_for_return()
        return

    # If multiple results, let user choose (simple list first)
    selected_person = results[0]
    if len(results) > 1:
        table = Table(title=f"Mehrere Treffer ({len(results)})", box=None)
        table.add_column("#", style="dim"); table.add_column("Name"); table.add_column("PNR")
        for idx, r in enumerate(results):
            table.add_row(str(idx+1), r.get('_display_name'), str(r.get('personalnummer', '')))
        console.print(table)
        
        try:
            sel_idx = int(Prompt.ask("Nummer wählen", default="1")) - 1
            if 0 <= sel_idx < len(results):
                selected_person = results[sel_idx]
            else: return
        except: return

    # Show FULL DETAILS for the selected person
    p = selected_person
    clear_screen()
    console.print(BANNER)
    
    # 1. Header Info
    console.print(f"\n[bold header]👤 {p.get('_display_name')}[/bold header]\n")
    
    # 2. Key-Value Table for Basic Info
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="white")
    
    # Extract interesting scalar fields
    fields = [
        ("Personalnummer", 'personalnummer'),
        ("Telefon (Dienst)", 'telefon'),
        ("Telefon (Privat)", 'telefon_privat'),
        ("Email", 'email'),
        ("Geburtsdatum", 'birthdate'),
        ("Login", 'maportal_lastLogin'),
        ("Letzte Aktivität", 'maportal_lastActivity'),
        ("Saldo Urlaub", 'saldo_urlaub'),
        ("Saldo ZA", 'saldo_za'),
        ("Valid From", 'validFrom'),
        ("Valid To", 'validTo'),
        ("Info Text", 'info'),
        ("GUID", 'guid'),
        ("User ID", 'externalId')
    ]
    
    for label, key in fields:
        val = str(p.get(key, ''))
        if val and val != "None":
            grid.add_row(label + ":", val)
            
    console.print(Panel(grid, title="Basisdaten", border_style="blue"))
    
    # 3. Complex Lists (Occupations, Skills, Groups)
    
    # Occupations
    occs = p.get('ressourceToOccupations', [])
    if occs:
        t_occ = Table(title="Rollen / Beschäftigung", box=None, show_edge=False, padding=(0,1))
        t_occ.add_column("Name"); t_occ.add_column("Beginn"); t_occ.add_column("Ende")
        for o in occs:
            t_occ.add_row(o.get('name', '-'), str(o.get('begin', ''))[:10], str(o.get('end', ''))[:10])
        console.print(t_occ)

    # Skills
    skills = p.get('staffToSkills', [])
    if skills:
        t_skill = Table(title="Qualifikationen / Skills (IDs)", box=None, show_edge=False, padding=(0,1))
        t_skill.add_column("Skill GUID/ID", style="dim"); t_skill.add_column("Beginn"); t_skill.add_column("Ende")
        for s in skills:
            # Try to show something readable if possible, otherwise GUID parts
            sid = s.get('skillDataGuid', '???')
            t_skill.add_row(sid[:20]+"...", str(s.get('begin', ''))[:10], str(s.get('end', ''))[:10])
        console.print(t_skill)
        
    # Groups
    groups = p.get('ressourceToGroups', [])
    if groups:
        t_grp = Table(title="Gruppen", box=None, show_edge=False, padding=(0,1))
        t_grp.add_column("Group GUID", style="dim"); t_grp.add_column("Beginn")
        for g in groups:
             gid = g.get('groupDataGuid', '???')
             t_grp.add_row(gid[:20]+"...", str(g.get('begin', ''))[:10])
        console.print(t_grp)

    # 4. Raw Dump Option
    console.print("\n[dim]Drücke 'r' für RAW JSON Dump, oder ENTER weiter...[/dim]")
    k = get_key()
    if k and k.lower() == 'r':
        console.print(Pretty(p))
        wait_for_return()
    elif k == KEY_ENTER:
        return

def show_future_duties(incode: Any, search_colleague: Optional[str] = None) -> None:
    with console.status("[bold green]Lade Dienstplan..."): duties = incode.load_future_duties()
    if not duties: 
        console.print("[info]Keine Fahrdienste.[/info]")
        wait_for_return()
        return

    title = "📅  Mein Dienstplan" if not search_colleague else f"🔍  Gemeinsame Dienste mit '{search_colleague}'"
    table = Table(title=title, header_style="header", expand=False, box=None, padding=(0, 1), show_header=True)
    table.add_column("Datum", style="info")
    table.add_column("Zeit", style="info")
    table.add_column("Ort", style="dim", min_width=15)
    table.add_column("Fzg", style="success")
    table.add_column("Besatzung", style="crew")
    
    monthly_stats: Dict[str, float] = defaultdict(float)
    found_any = False
    export_duties = []
    month_names = {1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni", 7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember"}
    
    for d in duties:
        try:
            b, e = datetime.strptime(d['begin'], '%Y-%m-%dT%H:%M:%S'), datetime.strptime(d['end'], '%Y-%m-%dT%H:%M:%S')
            h = (e - b).total_seconds() / 3600
            crew_str = ", ".join(d['crew']) if d['crew'] else "-"
            if search_colleague and search_colleague.lower() not in crew_str.lower(): continue
            found_any = True
            export_duties.append(d)
            month_key = f"{b.year}-{b.month:02d} ({month_names[b.month]})"
            monthly_stats[month_key] += h
            loc = d.get('location', '')
            if not loc and d.get('duty_type') == 'Vergangen':
                loc = "[dim]-[/dim]"
            table.add_row(b.strftime('%d.%m.%Y'), f"{b.strftime('%H:%M')}-{e.strftime('%H:%M')} ({h:g}h) ", loc, d['vehicle'] or "-", crew_str)
        except Exception: pass

    if not found_any: console.print(f"[info]Keine gemeinsamen Dienste mit '{search_colleague}' gefunden.[/info]")
    else:
        from rich import box
        table.box = box.SIMPLE_HEAD
        console.print(table)
        
        if not search_colleague:
            console.print("\n" + "─" * 50 + "\n") # Separator line
            
            # Hours Statistics
            stats_table = Table(title="[bold blue]Stunden-Statistik[/bold blue]", header_style="stats", box=box.SIMPLE_HEAD, padding=(0, 2))
            stats_table.add_column("Monat"); stats_table.add_column("Stunden", justify="right")
            for m, total in sorted(monthly_stats.items()): stats_table.add_row(m, f"{total:g} Std.")
            
            # Duty Count Statistics
            duty_counts = defaultdict(int)
            location_counts = defaultdict(int)
            
            vehicle_types = ["RTWA", "RTW", "KTW", "BTW", "NEF", "BKTW", "VEF"] 
            
            for d in duties:
                loc = d.get('location', '')
                if loc: location_counts[loc] += 1
                
                key = None
                vehicle = d.get('vehicle', '').upper()
                duty_type = d.get('duty_type', '')
                
                if vehicle:
                    for vt in vehicle_types:
                        if vt in vehicle:
                            key = vt
                            break
                    if not key: key = vehicle
                elif duty_type:
                    key = duty_type
                
                if key:
                    if key == "Beruflich" or key == "-": key = "Sonstige / Ohne Fzg."
                    duty_counts[key] += 1
            
            # Print Stats in a nice way
            from rich.columns import Columns
            
            count_table = Table(title="[bold blue]Dienst-Statistik[/bold blue]", header_style="stats", box=box.SIMPLE_HEAD, padding=(0, 2))
            count_table.add_column("Typ/Art"); count_table.add_column("Anzahl", justify="right")
            for k, v in sorted(duty_counts.items(), key=lambda item: item[1], reverse=True):
                count_table.add_row(k, f"{v}x")

            loc_table = Table(title="[bold blue]Dienststellen-Statistik[/bold blue]", header_style="stats", box=box.SIMPLE_HEAD, padding=(0, 2))
            loc_table.add_column("Dienststelle"); loc_table.add_column("Anzahl", justify="right")
            for k, v in sorted(location_counts.items(), key=lambda item: item[1], reverse=True):
                loc_table.add_row(k, f"{v}x")

            # Display tables side by side or neatly stacked
            console.print(Columns([stats_table, count_table, loc_table], equal=True, expand=True))
        
        opt_str = "'p' für PDF, 'c' für Kalender (iCal), 't' für PDF & Telegram"
        console.print(f"\n[dim]Drücke {opt_str}, oder eine beliebige andere Taste...[/dim]")
        
        flush_input()
        while True:
            k = get_key()
            if k:
                k = k.lower()
                # Clean timestamp for filenames: YYYY-MM-DD_HH-MM
                ts_readable = datetime.now().strftime('%Y-%m-%d_%H-%M')
                
                if k == 'p' or k == 't':
                    if search_colleague:
                        # Sanitize name
                        safe_name = "".join([c if c.isalnum() else "_" for c in search_colleague])
                        fn = f"Dienstplan_{safe_name}_{ts_readable}.pdf"
                    else:
                        fn = f"Mein_Dienstplan_{ts_readable}.pdf"

                    if export_to_pdf(export_duties, fn):
                        if k == 't':
                            msg = f"Dienstplan Export vom {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                            if send_pdf_via_bot(incode, fn, msg):
                                console.print("[success]PDF erfolgreich per Telegram gesendet![/success]")
                    wait_for_return()
                    break
                elif k == 'c':
                    fn = f"Dienstplan_{ts_readable}.ics"
                    if search_colleague: 
                        safe_name = "".join([c if c.isalnum() else "_" for c in search_colleague])
                        fn = f"Dienstplan_{safe_name}_{ts_readable}.ics"
                    
                    export_to_ics(export_duties, fn)
                    wait_for_return()
                    break
                else:
                    break

def show_daily_plan(incode: Any, date: Optional[datetime] = None, is_live: bool = False, override_plan: Optional[List[Any]] = None) -> Optional[List[Any]]:
    if not date: date = datetime.now()
    
    plan = None
    if override_plan is not None:
        plan = override_plan
    else:
        if not is_live:
            with console.status("[bold green]Lade Gesamten Tagesplan..."):
                plan = incode.load_daily_plan(date)
        else:
            plan = incode.load_daily_plan(date)
        
    if not plan:
        if not is_live: 
            console.print(f"[info]Kein Plan für {date.strftime('%d.%m.%Y')}.[/info]")
            wait_for_return()
        return None
        
    table = Table(title=f"🚑  Gesamter Tagesplan {date.strftime('%d.%m.%Y')}", header_style="header", expand=False, box=None, padding=(0, 1))
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
        console.print(BANNER)
        # print('\a') # Bell sound removed
        console.print(f"[live]● LIVE MODUS[/live]  [dim]Letztes Update: {datetime.now().strftime('%H:%M:%S')}[/dim]")
        if override_plan is not None:
             # If we are in live mode and updated, maybe show a small indicator
             pass
        console.print(table)
        return plan
    else: 
        console.print(table)
        
        opt_str = "'p' für PDF, 'c' für Kalender (iCal), 't' für PDF & Telegram"
        console.print(f"\n[dim]Drücke {opt_str}, oder eine beliebige andere Taste...[/dim]")
        
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
                                console.print("[success]PDF erfolgreich per Telegram gesendet![/success]")
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

def show_live_monitor(incode: Any) -> None:
    # 1. Date Selection
    options = [("🕒  Heute überwachen", "today"), ("🗓️  Anderes Datum wählen", "date")]
    sel = interactive_menu(options, title="📺  LIVE MONITOR SETUP")
    if sel is None: return

    target_date = datetime.now()
    if sel == "date":
        d = select_date_interactive()
        if d: target_date = d
        else: return # Cancelled
    
    # 2. Telegram Setup
    enable_telegram = False
    
    # Check if configured
    creds = load_credentials()
    has_telegram = creds and creds.get("telegram_token") and creds.get("allowed_user_id")
    
    if has_telegram:
        console.print("Telegram-Benachrichtigungen aktivieren (PDF bei Start & Änderung)?")
        console.print("[dim][j] Ja  •  [n] Nein  •  ESC Abbrechen[/dim]")
        while True:
            k = get_key()
            if not k: continue
            k = k.lower()
            if k == 'j':
                enable_telegram = True
                break
            elif k == 'n':
                enable_telegram = False
                break
            elif k == KEY_ESC or k == 'q':
                return
    else:
        console.print("[dim]Telegram nicht konfiguriert - Benachrichtigungen deaktiviert.[/dim]")
        time.sleep(1)
    
    # 3. Refresh Interval
    try:
        min_str = Prompt.ask("Aktualisierungs-Intervall (Minuten)", default="5")
        refresh_interval = int(min_str) * 60
        if refresh_interval < 60: refresh_interval = 60
    except:
        refresh_interval = 300
    
    last_plan = None
    
    clear_screen()
    console.print(f"[bold]Starte Monitor für {target_date.strftime('%d.%m.%Y')}...[/bold]")
    
    first_run = True

    while True:
        try:
            # Load Data
            current_plan = incode.load_daily_plan(target_date)
            
            # Check for changes
            has_changes = False
            if last_plan is None:
                has_changes = True # First load is always a "change"
            else:
                if current_plan != last_plan:
                    has_changes = True

            if has_changes:
                last_plan = current_plan
                
                # Update UI
                show_daily_plan(incode, date=target_date, is_live=True, override_plan=current_plan)
                
                # Handle Notifications
                if enable_telegram and current_plan:
                    # Prepare export data (similar logic to show_daily_plan export)
                    export_duties = []
                    for p in current_plan:
                        try:
                            cl = []
                            for r in ["FAHRER", "SANITAETER1", "SANITAETER2"]:
                                if r in p["crew"]: cl.append(p['crew'][r])
                            export_duties.append({
                                'begin': p['begin'].strftime('%Y-%m-%dT%H:%M:%S'),
                                'end': p['end'].strftime('%Y-%m-%dT%H:%M:%S'),
                                'location': "", 'vehicle': p['vehicle'], 'duty_type': "", 'crew': cl
                            })
                        except: pass
                    
                    ts = datetime.now().strftime('%H:%M')
                    # Optimized filename for live updates
                    fn = f"Live_Tagesplan_{target_date.strftime('%Y-%m-%d')}_{datetime.now().strftime('%H-%M')}.pdf"
                    
                    if export_to_pdf(export_duties, fn):
                        msg_text = f"Live-Update für {target_date.strftime('%d.%m.%Y')} (Stand: {ts})"
                        if first_run:
                            msg_text = f"Live-Monitor gestartet für {target_date.strftime('%d.%m.%Y')} (Stand: {ts})"
                        
                        try:
                            console.print(f"[dim]Sende Telegram Update...[/dim]")
                            send_pdf_via_bot(incode, fn, msg_text)
                            console.print(f"[success]Telegram gesendet.[/success]")
                        except Exception as e:
                            console.print(f"[error]Telegram Fehler: {e}[/error]")
                        finally:
                            if os.path.exists(fn):
                                os.remove(fn)
            
            first_run = False
            
            # Countdown loop
            start_time = time.time()
            with Live(transient=True) as live:
                while time.time() - start_time < refresh_interval:
                    remaining = int(refresh_interval - (time.time() - start_time))
                    live.update(f"\n[dim]Aktualisierung in {remaining}s. ESC zum Beenden...[/dim]")
                    
                    k = get_key(timeout=0.1)
                    if k == '\x1b' or (k and k.lower() == 'q'):
                        return

        except Exception as e:
            console.print(f"[error]Fehler im Live-Monitor Loop: {e}[/error]")
            # Wait a bit before retry to avoid spamming errors if network is down
            time.sleep(10)
