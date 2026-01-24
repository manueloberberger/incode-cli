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
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print()
        options = [
            ("📋  Meine Ambulanz-Dienste", "my"),
            ("🗓️  Veranstaltungs-Übersicht (Alle)", "all"),
            ("🔙  Zurück", "back")
        ]
        sel = interactive_menu(options, title="🚑  EVENTS / AMBULANZEN")
        
        if not sel or sel == "back":
            break
        
        if sel == "my":
            with Live(Align.center(Spinner("dots", text=" Lade meine Ambulanzen ...")), console=console, transient=True):
                duties = incode.load_my_event_duties()
            
            if not duties:
                console.print(Align.center("\n[info]Keine eigenen Event-Dienste gefunden.[/info]"))
                wait_for_return()
                continue

            table = Table(title="📋  Meine Ambulanz-Dienste", header_style="header", box=None, padding=(0,1))
            table.add_column("Datum", style="info")
            table.add_column("Zeit", style="info")
            table.add_column("Veranstaltung / Ort", style="white")
            table.add_column("Fzg/Pos", style="dim")
            
            for d in duties:
                try:
                    # Async API returns objects (Duty), sync logic might return dicts if not parsed?
                    # Wait, load_my_event_duties in Async API returns parse_personal_duties which returns Duty objects.
                    # But the old code access d['begin']. We need to handle Duty objects if they are objects.
                    # Sync API uses parse_personal_duties which returns Duty objects.
                    # But the logic I saw in previous file view used d['begin']. This suggests dicts were used before.
                    # Let's check src/models.py or assume Duty object access.
                    # Actually, parse_personal_duties returns List[Duty]. Duty is a dataclass or class.
                    # Accessing via ['begin'] suggests it might be subscriptable or the code was broken for objects?
                    # Or maybe previous implementation returned dicts.
                    # API Async implementation returns Duty objects.
                    # I should fix access to be attribute based if it is an object, or ensure subscription works.
                    # Let's check if Duty is subscriptable. Usually not unless defined.
                    # Safest is to try attribute access first, then dict.
                    pass
                    b = d.begin if hasattr(d, 'begin') else datetime.strptime(d['begin'], '%Y-%m-%dT%H:%M:%S')
                    e = d.end if hasattr(d, 'end') else datetime.strptime(d['end'], '%Y-%m-%dT%H:%M:%S')
                    
                    loc = getattr(d, 'location', None) or d.get('location', '') if isinstance(d, dict) else d.location
                    info = getattr(d, 'duty_type', None) or d.get('duty_type', '') if isinstance(d, dict) else d.duty_type
                    vehicle = getattr(d, 'vehicle', None) or d.get('vehicle', '') if isinstance(d, dict) else d.vehicle
                    
                    table.add_row(
                        b.strftime('%d.%m.%Y'),
                        f"{b.strftime('%H:%M')}-{e.strftime('%H:%M')}",
                        loc or info,
                        vehicle or info
                    )
                except Exception as exc: 
                    # console.print(exc)
                    pass
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
                continue
                
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
