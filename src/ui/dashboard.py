from collections import defaultdict
from datetime import datetime
from typing import Optional, Any, Dict, List

from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner
from rich.columns import Columns
from rich import box

from src.config import console, BANNER
from src.utils import clear_screen, wait_for_return, flush_input, get_key
from src.pdf import export_to_pdf
from src.ical import export_to_ics
from src.ui.components import send_pdf_via_bot

def show_future_duties(incode: Any, search_colleague: Optional[str] = None) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    
    if search_colleague:
        console.print(Align.center(f"[bold header]GEMEINSAME DIENSTE MIT '{search_colleague.upper()}'[/bold header]"))
    else:
        console.print(Align.center("[bold header]MEIN DIENSTPLAN[/bold header]"))
    
    console.print()
    with Live(Align.center(Spinner("dots", text=" Lade Dienstplan ...")), console=console, transient=True):
        duties = incode.load_future_duties(override_name=search_colleague)
    if not duties: 
        if search_colleague:
            console.print(Align.center(f"\n[info]Keine gemeinsamen Dienste mit '{search_colleague}' gefunden.[/info]"))
        else:
            console.print(Align.center("\n[info]Keine Dienste gefunden.[/info]"))
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
    export_duties: List[Dict[str, Any]] = []
    month_names = {1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni", 7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember"}
    
    for d in duties:
        try:
            # d is now a Duty object
            b, e = d.begin, d.end
            h = d.duration_hours
            crew_str = ", ".join(d.crew) if d.crew else "-"
            if search_colleague and search_colleague.lower() not in crew_str.lower(): continue
            found_any = True
            
            # For export, we might need a dict representation if export tools expect it
            # The export tools in pdf.py/ical.py currently handle dicts primarily but check type.
            # We should probably pass a dict or update those tools. 
            # Given constraints, let's create a dict for export to be safe for now.
            export_duties.append({
                'begin': b.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': e.strftime('%Y-%m-%dT%H:%M:%S'),
                'vehicle': d.vehicle,
                'location': d.location,
                'duty_type': d.duty_type,
                'crew': d.crew
            })
            
            month_key = f"{b.year}-{b.month:02d} ({month_names[b.month]})"
            monthly_stats[month_key] += h
            loc = d.location or ""
            if not loc and d.duty_type == 'Vergangen':
                loc = "[dim]-[/dim]"
            table.add_row(b.strftime('%d.%m.%Y'), f"{b.strftime('%H:%M')}-{e.strftime('%H:%M')} ({h:g}h) ", loc, d.vehicle or "-", crew_str)
        except Exception: pass

    if not found_any: 
        if search_colleague:
            console.print(Align.center(f"\n[info]Keine gemeinsamen Dienste mit '{search_colleague}' gefunden.[/info]"))
        else:
            console.print(Align.center("\n[info]Keine Dienste gefunden.[/info]"))
        wait_for_return()
    else:
        table.box = box.SIMPLE_HEAD
        console.print(Align.center(table))
        
        if not search_colleague:
            console.print(Align.center("\n" + "─" * 50 + "\n")) # Separator line
            
            # Hours Statistics
            stats_table = Table(title="[bold blue]Stunden-Statistik[/bold blue]", header_style="stats", box=box.SIMPLE_HEAD, padding=(0, 2))
            stats_table.add_column("Monat"); stats_table.add_column("Stunden", justify="right")
            total_all_hours = 0.0
            for m, total in sorted(monthly_stats.items()): 
                stats_table.add_row(m, f"{total:g} Std.")
                total_all_hours += total
            
            stats_table.add_section()
            stats_table.add_row("[bold]GESAMT[/bold]", f"[bold]{total_all_hours:g} Std.[/bold]")
            
            # Duty Count Statistics
            duty_counts: Dict[str, int] = defaultdict(int)
            location_counts: Dict[str, int] = defaultdict(int)
            
            vehicle_types = ["RTWA", "RTW", "KTW", "BTW", "NEF", "BKTW", "VEF"] 
            
            for d in duties:
                loc = d.location or ""
                if loc: location_counts[loc] += 1
                
                key = None
                vehicle = (d.vehicle or "").upper()
                duty_type = d.duty_type or ""
                
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
            
            count_table = Table(title="[bold blue]Dienst-Statistik[/bold blue]", header_style="stats", box=box.SIMPLE_HEAD, padding=(0, 2))
            count_table.add_column("Typ/Art"); count_table.add_column("Anzahl", justify="right")
            for k, v in sorted(duty_counts.items(), key=lambda item: item[1], reverse=True):
                count_table.add_row(k, f"{v}x")
            loc_table = Table(title="[bold blue]Dienststellen-Statistik[/bold blue]", header_style="stats", box=box.SIMPLE_HEAD, padding=(0, 2))
            loc_table.add_column("Dienststelle"); loc_table.add_column("Anzahl", justify="right")
            for k, v in sorted(location_counts.items(), key=lambda item: item[1], reverse=True):
                loc_table.add_row(k, f"{v}x")


            # Display tables side by side
            console.print(Align.center(Columns([stats_table, count_table, loc_table], align="center", expand=True)))

            # Display tables side by side or neatly stacked
        opt_str = "'p' für PDF, 'c' für Kalender (iCal), 't' für PDF & Telegram"
        console.print(Align.center(f"\n[dim]Drücke {opt_str}, oder eine beliebige andere Taste ...[/dim]"))
        
        flush_input()
        while True:
            key_input = get_key()
            if key_input:
                k_str = key_input.lower()
                # Clean timestamp for filenames: YYYY-MM-DD_HH-MM
                ts_readable = datetime.now().strftime('%Y-%m-%d_%H-%M')
                
                if k_str == 'p' or k_str == 't':
                    if search_colleague:
                        # Sanitize name
                        safe_name = "".join([c if c.isalnum() else "_" for c in search_colleague])
                        fn = f"Dienstplan_{safe_name}_{ts_readable}.pdf"
                    else:
                        fn = f"Mein_Dienstplan_{ts_readable}.pdf"

                    if export_to_pdf(export_duties, fn):
                        if k_str == 't':
                            msg = f"Dienstplan Export vom {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                            if send_pdf_via_bot(incode, fn, msg):
                                console.print("[success]PDF erfolgreich per Telegram gesendet !!![/success]")
                    wait_for_return()
                    break
                elif k_str == 'c':
                    fn = f"Dienstplan_{ts_readable}.ics"
                    if search_colleague: 
                        safe_name = "".join([c if c.isalnum() else "_" for c in search_colleague])
                        fn = f"Dienstplan_{safe_name}_{ts_readable}.ics"
                    
                    export_to_ics(export_duties, fn)
                    wait_for_return()
                    break
                else:
                    break
