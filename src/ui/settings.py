from src.config import console, BANNER, get_update_interval, set_update_interval, VERSION
from src.ui.components import interactive_menu
from src.utils import clear_screen, check_for_updates, update_app, wait_for_return, prompt_yes_no
import time
import sys
import os
from rich.align import Align
from typing import List, Tuple, Any

def show_settings_menu() -> None:
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print(Align.center("[bold]EINSTELLUNGEN[/bold]"))
        console.print()
        
        current_interval = get_update_interval()
        
        # Helper to format interval string
        def fmt_interval(seconds: int) -> str:
            if seconds == 0: return "Immer (jeder Start)"
            if seconds < 3600: return f"{seconds//60} Minuten"
            hours = seconds / 3600
            if hours.is_integer():
                return f"{int(hours)} Stunden"
            return f"{hours} Stunden"

        console.print(Align.center(f"Aktuelles Update-Intervall: [bold cyan]{fmt_interval(current_interval)}[/bold cyan]"))
        console.print()

        options: List[Tuple[str, Any]] = [
            ("🔄  Jetzt nach Updates suchen", "check_now"),
            ("⏱️   Häufigkeit der Update-Prüfung ändern", "interval"),
            ("🔙  Zurück", "back")
        ]
        
        selected = interactive_menu(options, title="EINSTELLUNGEN")
        
        if selected == "back" or selected is None:
            break
        elif selected == "interval":
            _change_update_interval()
        elif selected == "check_now":
            _manual_update_check()

def _manual_update_check() -> None:
    from rich.live import Live
    from rich.spinner import Spinner
    
    console.print()
    with Live(Align.center(Spinner("dots", text="[bold blue]Prüfe auf Updates ...[/bold blue]")), console=console, transient=True):
        new_version = check_for_updates(ignore_cache=True)
    
    if new_version:
        console.print(Align.center(f"[bold green]✨ Update verfügbar: v{VERSION} -> v{new_version}[/bold green]\n"))
        if prompt_yes_no("Möchtest du das Update jetzt installieren?"):
            if update_app():
                console.print(Align.center("[info]Die App wird neu gestartet ...[/info]"))
                time.sleep(1)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                wait_for_return()
        else:
            wait_for_return()
    else:
        console.print(Align.center("[green]Deine Version ist aktuell![/green]\n"))
        wait_for_return()

def _change_update_interval() -> None:
    current = get_update_interval()
    intervals = [
        ("Immer bei jedem Start", 0),
        ("Alle 30 Minuten", 1800),
        ("Alle 1 Stunde", 3600),
        ("Alle 6 Stunden (Standard)", 21600),
        ("Alle 12 Stunden", 43200),
        ("Einmal täglich (24h)", 86400)
    ]
    
    menu_options = []
    for label, val in intervals:
        prefix = "✅ " if val == current else "   "
        menu_options.append((f"{prefix}{label}", val))
        
    menu_options.append(("🔙  Zurück", -1))
    
    selection = interactive_menu(menu_options, title="UPDATE-HÄUFIGKEIT WÄHLEN")
    
    if selection is not None and selection != -1:
        set_update_interval(selection)
        console.print(Align.center(f"[green]Einstellung gespeichert![/green]"))
