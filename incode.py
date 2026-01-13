import os
import sys
import time
import shutil
from datetime import datetime
from typing import Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rich.prompt import Prompt
from rich.console import Console
from rich.align import Align
from rich.table import Table
from rich.text import Text
try:
    from src.config import console, BANNER, load_credentials, save_credentials, update_credentials
    from src.api import IncodeRequests
    from src.ui import show_future_duties, show_daily_plan, show_live_monitor, interactive_menu, select_date_interactive, show_staff_search, show_absences, show_events_menu
    from src.utils import clear_screen, check_for_updates, update_app, wait_for_return
    from src.bot import IncodeBot
except ImportError as e:
    print(f"Fehler: Abhängigkeiten konnten nicht geladen werden ({e}).")
    print("Bitte führe 'pip install -r requirements.txt' aus.")
    sys.exit(1)

class CenteredPrompt(Prompt):
    prompt_suffix = ""
    def make_prompt(self, default: Any) -> Text:
        return self.prompt

def setup_auth():
    creds = load_credentials()
    if creds:
        u, p = creds['username'], creds['password']
        base_url = creds.get('base_url')
        extra_guids = creds.get('extra_guids')
        console.print(Align.center(f"Verwende gespeicherte Zugangsdaten für [info]{u}[/info]"))
    else:
        width = shutil.get_terminal_size().columns
        padding = (width // 2) - 4
        
        console.print() # Spacer
        console.print(Align.center("[bold]Incode Benutzername[/bold]"))
        u = CenteredPrompt.ask(" " * max(0, padding) + "[bold green]>[/bold green] ")
        
        console.print() # Spacer
        console.print(Align.center("[bold]Passwort[/bold]"))
        p = CenteredPrompt.ask(" " * max(0, padding) + "[bold green]>[/bold green] ", password=True)
        
        console.print() # Spacer
        base_url = "https://dienstplan.k.roteskreuz.at" 
        extra_guids = None
        save_credentials(u, p, base_url, extra_guids, None)
    
    return u, p, base_url, extra_guids

def run_cli():
    clear_screen()
    console.print(Align.center(BANNER))
    
    # Check for updates
    try:
        from rich.spinner import Spinner
        from rich.live import Live
        with Live(Align.center(Spinner("dots", text="[dim]Prüfe auf Updates ...[/dim]")), console=console, transient=True):
            has_update = check_for_updates()
            
        if has_update:
            console.print(Align.center("\n[bold yellow]✨ Ein Update ist verfügbar![/bold yellow]"))
            # Custom centered prompt logic for update
            width = shutil.get_terminal_size().columns
            padding = (width // 2) - 30 # Approx center
            
            console.print(Align.center("Möchtest du das Update jetzt automatisch installieren?"))
            ans = CenteredPrompt.ask(" " * max(0, (width // 2) - 2) + "[bold green]>[/bold green] ", choices=["j", "n"], default="j")
            
            if ans == "j":
                if update_app():
                    console.print(Align.center("[info]Die App wird neu gestartet ...[/info]"))
                    time.sleep(1)
                    # Restart the script
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    wait_for_return()
            else:
                console.print(Align.center("\nNutze [bold green]git pull[/bold green] um die neueste Version manuell zu erhalten."))
                console.print(Align.center("[dim](Denke danach daran, 'pip install -r requirements.txt' auszuführen)[/dim]\n"))
                wait_for_return()
            clear_screen()
            console.print(Align.center(BANNER))
    except Exception:
        pass # Ignore errors during update check to not block startup
    
    u, p, base_url, extra_guids = setup_auth()
        
    incode = IncodeRequests(base_url, extra_guids)
    
    s, m = incode.login(u, p)
    if not s: 
        console.print(Align.center(f"[error]{m}[/error]"))
        if Prompt.ask("Zugangsdaten löschen?", choices=["j", "n"], default="n") == "j":
            if os.path.exists('.credentials.json'): os.remove('.credentials.json')
        return
    
    menu_options = [
        ("📅  Mein Dienstplan", "future"),
        ("🌴  Meine Abwesenheiten", "absences"),
        ("🚑  Events / Ambulanzdienste", "events"),
        ("🚑  Tagesplan (Heute)", "today"),
        ("📆  Tagesplan (Datum wählen)", "date"),
        ("📒  Mitarbeiter-Verzeichnis", "staff"),
        ("🔍  Gemeinsame Dienste suchen", "colleague"),
        ("📺  Live-Monitor", "live"),
        ("🤖  Telegram Bot", "bot"),
        ("🚪  Beenden", "exit")
    ]

    while True:
        selection = interactive_menu(menu_options)
        
        if selection == "future":
            show_future_duties(incode)
        elif selection == "absences":
            show_absences(incode)
        elif selection == "events":
            show_events_menu(incode)
        elif selection == "today":
            show_daily_plan(incode)
        elif selection == "date":
            target_date = select_date_interactive()
            if target_date:
                show_daily_plan(incode, target_date)
        elif selection == "staff":
            show_staff_search(incode)
        elif selection == "colleague":
            width = shutil.get_terminal_size().columns
            padding = (width // 2) - 4
            console.print() # Spacer
            console.print(Align.center("[bold]Gemeinsame Dienste suchen[/bold]"))
            console.print(Align.center("[dim]Name des Kollegen eingeben ...[/dim]"))
            console.print() # Added blank line
            name = CenteredPrompt.ask(" " * max(0, padding) + "[bold green]>[/bold green] ")
            if name: 
                console.print() # Spacer
                show_future_duties(incode, search_colleague=name)
        elif selection == "live":
            show_live_monitor(incode)
        elif selection == "bot":
            start_bot_mode(incode)
        elif selection == "exit" or selection is None:
            clear_screen()
            console.print(Align.center("[dim]Auf Wiedersehen![/dim]"))
            break

def start_bot_mode(incode_instance=None, debug=False):
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold blue]Starte Telegram Bot Modus ...[/bold blue]"))
    console.print()
    
    if not incode_instance:
        u, p, base_url, extra_guids = setup_auth()
        incode_instance = IncodeRequests(base_url, extra_guids)
    
    bot = IncodeBot(incode_instance)
    bot.run(debug=debug)

def show_help():
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold cyan]Incode CLI - Hilfesystem[/bold cyan]"))
    console.print()
    
    help_text = [
        ("Befehl", "Beschreibung"),
        ("---", "---"),
        ("./incode", "Startet das interaktive Hauptmenü (Standard)."),
        ("./incode bot", "Startet den Telegram Bot Modus."),
        ("./incode bot --debug", "Startet den Bot mit erweiterten technischen Logs."),
        ("./incode --help", "Zeigt diese Hilfeübersicht an."),
        ("./incode --version", "Zeigt die aktuelle Programmversion.")
    ]
    
    table = Table(box=None, header_style="bold magenta", padding=(0, 2))
    table.add_column("Befehl", style="green")
    table.add_column("Beschreibung", style="white")
    
    for cmd, desc in help_text[2:]:
        table.add_row(cmd, desc)
        
    console.print(Align.center(table))
    console.print()
    wait_for_return()

if __name__ == "__main__":
    try:
        from src.config import VERSION
        
        if "--help" in sys.argv or "-h" in sys.argv:
            show_help()
            sys.exit(0)
            
        if "--version" in sys.argv:
            console.print(f"Incode CLI v{VERSION}")
            sys.exit(0)

        debug_mode = "--debug" in sys.argv
        if len(sys.argv) > 1 and "bot" in sys.argv:
            start_bot_mode(debug=debug_mode)
        else:
            run_cli()
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer.")
