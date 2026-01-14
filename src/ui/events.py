from datetime import datetime
from typing import Any

from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner

from src.config import console, BANNER
from src.utils import clear_screen, wait_for_return
from src.ui.components import interactive_menu

def show_events_menu(incode: Any) -> None:
    console.print()
    options = [
        ("📋  Meine Ambulanz-Dienste", "my"),
        ("🗓️  Veranstaltungs-Übersicht (Alle)", "all")
    ]
    sel = interactive_menu(options, title="🚑  EVENTS / AMBULANZEN")
    if not sel: return
    
    if sel == "my":
        with Live(Align.center(Spinner("dots", text=" Lade meine Ambulanzen ...")), console=console, transient=True):
            duties = incode.load_my_event_duties()
        
        if not duties:
            console.print(Align.center("\n[info]Keine eigenen Event-Dienste gefunden.[/info]"))
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
        console.print(Align.center(table))
        wait_for_return()

    elif sel == "all":
        clear_screen()
        console.print(Align.center(BANNER))
        console.print()
        console.print(Align.center("[bold header]VERANSTALTUNGS-KALENDER[/bold header]"))
        console.print()
        with Live(Align.center(Spinner("dots", text=" Lade Veranstaltungs-Plan ...")), console=console, transient=True):
            # Load 3 months by default
            plan = incode.load_events_plan()
            
        if not plan:
            console.print(Align.center("\n[info]Keine Veranstaltungen gefunden (oder keine Berechtigung).[/info]"))
            wait_for_return()
            return
            
        # Group by Date
        plan.sort(key=lambda x: x['begin'] if x['begin'] else datetime.min)
        
        console.print(Align.center("[bold]🗓️  Veranstaltungs-Kalender[/bold]"))
        console.print()
        
        table = Table(header_style="header", box=None, padding=(0,1))
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
            
        console.print(Align.center(table))
        wait_for_return()
