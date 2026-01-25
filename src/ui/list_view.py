from datetime import datetime, timedelta, date
from typing import Optional, List, Any, Dict
from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel

from src.config import console, BANNER
from src.utils import clear_screen, wait_for_return, flush_input, get_key
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
    results = []
    
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
                    b = datetime.strptime(item['begin'], '%Y-%m-%dT%H:%M:%S')
                else:
                    b = item['begin']
                
                d = b.date()
                if d not in all_data: all_data[d] = []
                all_data[d].append(item)
                
        except Exception as e:
            console.print(f"[red]Fehler beim Laden: {e}[/red]")
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
                b = p.get('begin')
                if isinstance(b, str): b = datetime.strptime(b, '%Y-%m-%dT%H:%M:%S')
                e = p.get('end')
                if isinstance(e, str): e = datetime.strptime(e, '%Y-%m-%dT%H:%M:%S')
                
                crew_list = []
                # Basic crew parsing if simple dict
                if isinstance(p.get('crew'), dict):
                     for r in ["FAHRER", "SANITAETER1", "SANITAETER2"]:
                        if r in p["crew"]: crew_list.append(p['crew'][r])
                
                t.add_row(
                    f"{b.strftime('%H:%M')}-{e.strftime('%H:%M')}",
                    p.get('vehicle', '??'),
                    ", ".join(crew_list)
                )
            
            pager_console.print(t)
            pager_console.print("[dim]" + ("- " * 20) + "[/dim]")
            
