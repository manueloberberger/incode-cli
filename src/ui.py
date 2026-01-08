import os
import shutil
import subprocess
import time
import sys
import calendar
import re
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
    show_details = False
    
    # Helper for nice dates
    def fmt_date(s):
        if not s or len(str(s)) < 10: return "-"
        try:
            return datetime.strptime(str(s)[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
        except: return s

    while True:
        clear_screen()
        console.print(BANNER)
        console.print(f"\n[bold header]👤 {p.get('_display_name')}[/bold header]\n")
        
        # Try to extract Service Number (Dienstnummer) from Occupations
        service_number = "-"
        occs = p.get('ressourceToOccupations', [])
        for o in occs:
            name = str(o.get('name', ''))
            parts = name.split('.')
            if parts and parts[0].isdigit():
                service_number = parts[0]
                break
            if name.split(' ')[0].isdigit():
                 service_number = name.split(' ')[0]

        # --- BASIC INFO ---
        grid_basic = Table.grid(expand=True, padding=(0, 2))
        grid_basic.add_column(style="bold cyan", justify="right")
        grid_basic.add_column(style="white")
        
        basic_fields = [
            ("Dienstnummer", lambda _: service_number),
            ("Incode-ID (PNR)", 'personalnummer'),
            ("Rolle (Maportal)", 'maportal_role'),
            ("Telefon (Dienst)", 'telefon'),
            ("Telefon (Privat)", 'telefon_privat'),
            ("Email", 'email')
        ]
        
        for label, key in basic_fields:
            if callable(key): val = key(p)
            else: val = str(p.get(key, ''))
            if val and val != "None" and val != "-":
                grid_basic.add_row(label + ":", str(val))
        
        console.print(Panel(grid_basic, title="Kontakt & Basisdaten", border_style="blue"))

        # --- DETAILS ---
        if show_details:
            # Extended Attributes
            grid_ext = Table.grid(expand=True, padding=(0, 2))
            grid_ext.add_column(style="bold cyan", justify="right")
            grid_ext.add_column(style="white")

            ext_fields = [
                ("Benutzername", 'maportal_manualName'),
                ("Geburtsdatum", lambda x: fmt_date(x.get('birthdate'))),
                ("Letzter Login", lambda x: fmt_date(x.get('maportal_lastLogin'))),
                ("Urlaubssaldo", 'saldo_urlaub'),
                ("ZA-Saldo", 'saldo_za'),
                ("Gültig ab", lambda x: fmt_date(x.get('validFrom'))),
                ("Gültig bis", lambda x: fmt_date(x.get('validTo'))),
                ("Erstellt", 'created'),
                ("Bearbeitet", 'updated'),
                ("Ursprung", 'origin'),
                ("Info", 'info')
            ]
            
            has_ext = False
            for label, key in ext_fields:
                if callable(key): val = key(p)
                else: val = str(p.get(key, ''))
                if val and val != "None" and val != "-":
                    grid_ext.add_row(label + ":", str(val))
                    has_ext = True
            
            if has_ext:
                console.print(Panel(grid_ext, title="Weitere Details", border_style="dim"))

            from rich import box
            
            # Roles Table
            if occs:
                t_occ = Table(title="Rollen / Beschäftigung", box=box.ROUNDED, show_edge=True, padding=(0,1), expand=True)
                t_occ.add_column("Bezeichnung", style="bold white")
                t_occ.add_column("Beginn", style="dim")
                t_occ.add_column("Ende", style="dim")
                t_occ.add_column("Ext. ID", style="dim")
                for o in occs:
                    t_occ.add_row(o.get('name', '-'), fmt_date(o.get('begin')), fmt_date(o.get('end')), o.get('externalId', ''))
                console.print(t_occ)

            # Skills
            skills = p.get('staffToSkills', [])
            if skills:
                t_skill = Table(title=f"Qualifikationen ({len(skills)})", box=box.ROUNDED, show_edge=True, padding=(0,1), expand=True)
                t_skill.add_column("Skill", style="cyan") # Using ExternalID as name proxy
                t_skill.add_column("Beginn", style="white")
                t_skill.add_column("Ende", style="dim")
                for s in skills:
                    t_skill.add_row(s.get('externalId', '-'), fmt_date(s.get('begin')), fmt_date(s.get('end')))
                console.print(t_skill)

            # Groups
            groups = p.get('ressourceToGroups', [])
            if groups:
                t_grp = Table(title=f"Gruppen-Zugehörigkeit ({len(groups)})", box=box.ROUNDED, show_edge=True, padding=(0,1), expand=True)
                t_grp.add_column("Gruppen GUID", style="dim")
                t_grp.add_column("Beginn", style="white")
                t_grp.add_column("Ende", style="dim")
                for g in groups:
                    t_grp.add_row(g.get('groupDataGuid', '')[:25] + "...", fmt_date(g.get('begin')), fmt_date(g.get('end')))
                console.print(t_grp)

        # Footer
        toggle_txt = "Details ausblenden" if show_details else "Details anzeigen"
        console.print(f"\n[dim]Drücke 'd' für {toggle_txt}, 'r' für RAW Dump, oder ENTER zum Beenden...[/dim]")
        
        k = get_key()
        if k and k.lower() == 'd':
            show_details = not show_details
        elif k and k.lower() == 'r':
            console.print(Pretty(p))
            wait_for_return()
        elif k == KEY_ENTER or (k and k.lower() == 'q') or k == KEY_ESC:
            return

def get_holidays(year: int) -> List[datetime.date]:
    """Returns a list of Austrian holidays for the given year."""
    # Fixed
    holidays = [
        datetime(year, 1, 1).date(),
        datetime(year, 1, 6).date(),
        datetime(year, 5, 1).date(),
        datetime(year, 8, 15).date(),
        datetime(year, 10, 10).date(),
        datetime(year, 10, 26).date(),
        datetime(year, 11, 1).date(),
        datetime(year, 12, 8).date(),
        datetime(year, 12, 24).date(),
        datetime(year, 12, 25).date(),
        datetime(year, 12, 26).date(),
        datetime(year, 12, 31).date()
    ]
    
    # Variable (Easter based)
    a = year % 19; b = year // 100; c = year % 100
    d = b // 4; e = b % 4; f = (b + 8) // 25
    g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    dy = ((h + l - 7 * m + 114) % 31) + 1
    easter = datetime(year, mo, dy).date()
    
    # Ostersonntag (0), Ostermontag (+1), Himmelfahrt (+39), Pfingstsonntag (+49), Pfingstmontag (+50), Fronleichnam (+60)
    holidays.append(easter)                      # Easter Sunday
    holidays.append(easter + timedelta(days=1))  # Easter Monday
    holidays.append(easter + timedelta(days=39)) # Ascension
    holidays.append(easter + timedelta(days=49)) # Whit Sunday
    holidays.append(easter + timedelta(days=50)) # Whit Monday
    holidays.append(easter + timedelta(days=60)) # Corpus Christi
    
    return holidays

def show_absences(incode: Any) -> None:
    with console.status("[bold green]Lade Abwesenheiten..."):
        # Try the dedicated endpoint first (this was the v1.7 behavior)
        absences = incode.load_absences()
        
        # Fallback to duties only if absolutely nothing found in dedicated absences
        if not absences:
             absences = incode.load_future_duties(filter_mode='only_absences')

    if not absences: 
        console.print("[info]Keine geplanten Abwesenheiten gefunden.[/info]")
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
        
    console.print(table)
    console.print(Panel(f"[bold]Verbrauchter Urlaub:[/bold] [cyan]{total_vacation_days} Tage[/cyan] (Netto, ohne So/Feiertage)", style="white", expand=False))
    wait_for_return()

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
                                if r in p["crew"]:
                                    cl.append(p['crew'][r])
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

def show_events_menu(incode: Any) -> None:
    options = [
        ("📋  Meine Ambulanz-Dienste", "my"),
        ("🗓️  Veranstaltungs-Übersicht (Alle)", "all")
    ]
    sel = interactive_menu(options, title="🚑  EVENTS / AMBULANZEN")
    if not sel: return
    
    if sel == "my":
        with console.status("[bold green]Lade meine Ambulanzen..."):
            duties = incode.load_my_event_duties()
        
        if not duties:
            console.print("[info]Keine eigenen Event-Dienste gefunden.[/info]")
            wait_for_return()
            return

        table = Table(title="📋  Meine Ambulanz-Dienste", header_style="header", box=None, padding=(0,1))
        table.add_column("Datum", style="info")
        table.add_column("Zeit", style="info")
        table.add_column("Veranstaltung / Ort", style="white")
        table.add_column("Fzg/Pos", style="dim")
        
        for d in duties:
            try:
                b = datetime.strptime(d['begin'], '%Y-%m-%dT%H:%M:%S')
                e = datetime.strptime(d['end'], '%Y-%m-%dT%H:%M:%S')
                
                loc = d.get('location', '')
                info = d.get('duty_type', '') 
                
                table.add_row(
                    b.strftime('%d.%m.%Y'),
                    f"{b.strftime('%H:%M')}-{e.strftime('%H:%M')}",
                    loc or info,
                    d.get('vehicle', '') or info
                )
            except: pass
        console.print(table)
        wait_for_return()
        
    elif sel == "all":
        with console.status("[bold green]Lade Veranstaltungs-Plan..."):
            # Load 3 months by default
            plan = incode.load_events_plan()
            
        if not plan:
            console.print("[info]Keine Veranstaltungen gefunden (oder keine Berechtigung).[/info]")
            wait_for_return()
            return
            
        # Group by Date
        plan.sort(key=lambda x: x['begin'] if x['begin'] else datetime.min)
        
        table = Table(title="🗓️  Veranstaltungs-Kalender", header_style="header", box=None, padding=(0,1))
        table.add_column("Datum", style="bold")
        table.add_column("Zeit", style="dim")
        table.add_column("Veranstaltung / Ort", style="white")
        table.add_column("Besatzung", style="crew")
        
        for p in plan:
            b, e = p['begin'], p['end']
            if not b or not e: continue
            
            crew_list = []
            # 'crew' is now a dict with unique keys, values are names
            for name in p.get('crew', {}).values():
                crew_list.append(name)
            
            # Add open slots info
            open_slots = p.get('open_slots', 0)
            if open_slots > 0:
                crew_list.append(f"[red]Noch {open_slots} Plätze !!![/red]")
            
            event_name = p.get('vehicle', 'Event')
            location = p.get('location', '')
            
            display_name = event_name
            if location and location not in event_name:
                display_name += f"\n[dim]({location})[/dim]"
            
            table.add_row(
                b.strftime('%d.%m.%Y'),
                f"{b.strftime('%H:%M')}-{e.strftime('%H:%M')}",
                display_name,
                ", ".join(crew_list) or "[dim]-[/dim]"
            )
            
        console.print(table)
        wait_for_return()