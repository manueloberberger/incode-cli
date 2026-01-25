from datetime import datetime, timedelta, date
from typing import List, Any, Dict
from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel

from src.config import console, BANNER
from src.utils import clear_screen, wait_for_return, get_key
from src.ui import interactive_menu

def show_plan_list(incode: Any) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold cyan]Tagespläne auflisten[/bold cyan]"))
    console.print()
    
    # 1. Ask for Range
    options = [
        ("Nächste 7 Tage", 7),
        ("Nächste 14 Tage", 14),
        ("Nächste 21 Tage", 21),
        ("Kommender Monat (30 Tage)", 30),
        ("🔙  Zurück", "back")
    ]
    
    selection = interactive_menu(options, title="ZEITRAUM WÄHLEN")
    if selection == "back" or not selection:
        return
        
    days = int(selection)
    
    # 2. Fetch Data
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=days-1)
    
    console.print()

    
    # We use a custom fetch loop or if we exposed the range fetch in sync API we use that
    # Since api_async.py's load_daily_plan is single day, but _fetch_daily_plan_items handles ranges...
    # We can try to access the internal async method via a helper or just loop.
    # Given we proved _fetch_daily_plan_items works for ranges in test_range.py, let's use that efficiently.
    # But IncodeRequests (sync) doesn't expose it directly.
    # We will just loop load_daily_plan for now (parallelized in background by async loop if we did it right, 
    # but wrapper is sync).
    # actually api.py wrapper is: loop.run_until_complete(self.client.load_daily_plan(date))
    # This is serial. To make it fast we need a new method in api.py "load_daily_plans_range".
    
    # Let's check api.py first. It does not have range fetch.
    # Use simple loop with spinner first. 
    
    all_data: Dict[date, List[Any]] = {}
    
    with Live(Align.center(Spinner("dots", text=f" Lade Pläne für {days} Tage ...")), console=console, transient=True):
        # We can actually use the client's internal methods if we access .client (AsyncIncodeRequests)
        # But we need to run it in the loop.
        # Let's implement a range fetch in the sync wrapper on the fly or just loop.
        # Loop is safest without modifying API structure too much right now.
        
        # ACTUALLY: test_range.py showed we CAN fetch range in one request!
        # logic: await client._fetch_daily_plan_items(start, end)
        # We should expose this in api.py
        
        # Assuming we will update api.py to expose `load_daily_plan_range`
        # For now, we utilize the private method access via run_until_complete
        
        try:
            # We need datetime objects
            sd_dt = datetime.combine(start_date, datetime.min.time())
            ed_dt = datetime.combine(end_date, datetime.max.time())
            
            raw_items = incode.loop.run_until_complete(incode.client._fetch_daily_plan_items(sd_dt, ed_dt))
            
            # Sort items into days
            for item in raw_items:
                if not item.get('begin'): continue
                if isinstance(item['begin'], str):
                    duty_begin = datetime.strptime(item['begin'], '%Y-%m-%dT%H:%M:%S')
                else:
                    duty_begin = item['begin']
                
                d = duty_begin.date()
                if d not in all_data: all_data[d] = []
                all_data[d].append(item)
                
        except Exception as ex:
            console.print(f"[red]Fehler beim Laden: {ex}[/red]")
            wait_for_return()
            return

    # 3. Display Loop
    if not all_data:
        console.print(Align.center("[yellow]Keine Dienste in diesem Zeitraum gefunden.[/yellow]"))
        wait_for_return()
        return

    # Sort days
    sorted_days = sorted(all_data.keys())
    
    # Simple Pager
    from rich.console import Console
    pager_console = Console(force_terminal=True)
    
    with pager_console.pager():
        for d in sorted_days:
            # Day Header
            weekday = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][d.weekday()]
            pager_console.print(f"\n[bold white on blue] {weekday}, {d.strftime('%d.%m.%Y')} [/bold white on blue]")
            
            items = all_data[d]
            # specific sorting: vehicle name? begin time?
            items.sort(key=lambda x: (x.get('vehicle', ''), x.get('begin')))
            
            # Sub-table
            t = Table(box=None, show_header=False, padding=(0,1))
            t.add_column("Time", style="dim")
            t.add_column("Vehicle", style="bold green")
            t.add_column("Crew")
            
            for p in items:
                duty_begin = p.get('begin')
                if isinstance(duty_begin, str): duty_begin = datetime.strptime(duty_begin, '%Y-%m-%dT%H:%M:%S')
                duty_end = p.get('end')
                if isinstance(duty_end, str): duty_end = datetime.strptime(duty_end, '%Y-%m-%dT%H:%M:%S')
                
                crew_list = []
                # Basic crew parsing if simple dict
                if isinstance(p.get('crew'), dict):
                     for r in ["FAHRER", "SANITAETER1", "SANITAETER2"]:
                        if r in p["crew"]: crew_list.append(p['crew'][r])
                
                t.add_row(
                    f"{duty_begin.strftime('%H:%M')}-{duty_end.strftime('%H:%M')}",
                    p.get('vehicle', '??'),
                    ", ".join(crew_list)
                )
            
            pager_console.print(t)
            pager_console.print("[dim]" + ("- " * 20) + "[/dim]")
            
    # Flatten data for export
    flat_export_data = []
    for d in sorted_days:
        items = all_data[d]
        # Sort assumed done in display loop, but good to be sure
        items.sort(key=lambda x: (x.get('vehicle', ''), x.get('begin')))
        for p in items:
            flat_export_data.append(p)

    from src.pdf import export_to_pdf
    from src.ui.components import send_pdf_via_bot
    
    # Clear screen after pager to show clean menu
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center(Panel(f"[bold]Liste mit {len(flat_export_data)} Diensten in {days} Tagen geladen.[/bold]", title="Status", border_style="green")))
    console.print()
    
    console.print(Align.center("[bold cyan]Möchtest du diese Liste exportieren?[/bold cyan]"))
    console.print()
    console.print(Align.center("[dim]Drücke 'p' für PDF-Export[/dim]"))
    console.print(Align.center("[dim]Drücke 't' für Export & Senden an Telegram[/dim]"))
    console.print()
    console.print(Align.center("[dim]Drücke Enter um ohne Export zurückzukehren[/dim]"))
    console.print()
            
    while True:
        k = get_key()
        if not k or k == '\n' or k == '\r': break
        k = k.lower()
        
        if k == 'p' or k == 't':
            ts = datetime.now().strftime('%Y-%m-%d_%H-%M')
            fn = f"Tagesplaene_Liste_{ts}.pdf"
            title = f"Tagespläne ({days} Tage)"
            
            with Live(Align.center(Spinner("dots", text=" Erstelle PDF ...")), console=console, transient=True):
                success = export_to_pdf(flat_export_data, fn, title_text=title)
            
            if success:
                console.print(Align.center(f"[success]PDF erstellt: {fn}[/success]"))
                if k == 't':
                    if send_pdf_via_bot(incode, fn, f"Export Tagespläne ({days} Tage)"):
                         console.print(Align.center("[success]Erfolgreich an Telegram gesendet![/success]"))
                
                # Wait before returning so user sees success message
                wait_for_return()
            break
        elif k == 'q':
            break
