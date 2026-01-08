import os
import sys
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rich.prompt import Prompt
from rich.console import Console
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

def setup_auth():
    creds = load_credentials()
    if creds:
        u, p = creds['username'], creds['password']
        base_url = creds.get('base_url')
        extra_guids = creds.get('extra_guids')
        console.print(f"Verwende gespeicherte Zugangsdaten für [info]{u}[/info]")
    else:
        u = Prompt.ask("User")
        p = Prompt.ask("Pass")
        base_url = "https://dienstplan.k.roteskreuz.at" 
        extra_guids = None
        save_credentials(u, p, base_url, extra_guids, None)
    
    return u, p, base_url, extra_guids

def run_cli():
    clear_screen()
    console.print(BANNER)
    
    # Check for updates
    try:
        with console.status("[dim]Prüfe auf Updates...[/dim]", spinner="dots"):
            has_update = check_for_updates()
            
        if has_update:
            console.print("\n[bold yellow]✨ Ein Update ist verfügbar![/bold yellow]")
            if Prompt.ask("Möchtest du das Update jetzt automatisch installieren?", choices=["j", "n"], default="j") == "j":
                if update_app():
                    console.print("[info]Die App wird neu gestartet...[/info]")
                    time.sleep(1)
                    # Restart the script
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    wait_for_return()
            else:
                console.print("\nNutze [bold green]git pull[/bold green] um die neueste Version manuell zu erhalten.")
                console.print("[dim](Denke danach daran, 'pip install -r requirements.txt' auszuführen)[/dim]\n")
                wait_for_return()
            clear_screen()
            console.print(BANNER)
    except Exception:
        pass # Ignore errors during update check to not block startup
    
    u, p, base_url, extra_guids = setup_auth()
        
    incode = IncodeRequests(base_url, extra_guids)
    
    s, m = incode.login(u, p)
    if not s: 
        console.print(f"[error]{m}[/error]")
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
            name = Prompt.ask("Name des Kollegen")
            if name: show_future_duties(incode, search_colleague=name)
        elif selection == "live":
            show_live_monitor(incode)
        elif selection == "bot":
            start_bot_mode(incode)
        elif selection == "exit" or selection is None:
            clear_screen()
            console.print("[dim]Auf Wiedersehen![/dim]")
            break

def start_bot_mode(incode_instance=None):
    console.print("[bold blue]Starte Telegram Bot Modus...[/bold blue]")
    
    if not incode_instance:
        u, p, base_url, extra_guids = setup_auth()
        incode_instance = IncodeRequests(base_url, extra_guids)
        # Login is handled lazily or checked inside bot methods usually, 
        # but good to ensure instance is ready.
    
    bot = IncodeBot(incode_instance)
    bot.run()

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "bot":
            start_bot_mode()
        else:
            run_cli()
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer.")
