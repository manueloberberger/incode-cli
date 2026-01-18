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
    from src.config import console, BANNER, load_credentials, save_credentials, update_credentials, remove_user, get_storage_status
    from src.utils import centered_input
    from src.api import IncodeRequests
    from src.ui import show_future_duties, show_daily_plan, show_live_monitor, interactive_menu, select_date_interactive, show_staff_search, show_absences, show_events_menu, show_colleague_search
    from src.utils import clear_screen, check_for_updates, update_app, wait_for_return, get_key, KEY_LEFT, KEY_RIGHT, KEY_ENTER, KEY_LEFT_ALT, KEY_RIGHT_ALT, centered_input, prompt_yes_no
    from src.bot import IncodeBot
except ImportError as e:
    print(f"Fehler: Abhängigkeiten konnten nicht geladen werden ({e}).")
    print("Bitte führe 'pip install -r requirements.txt' aus.")
    sys.exit(1)



def _prompt_new_user():
    width = shutil.get_terminal_size().columns
    padding = (width // 2) - 4
    
    console.print()
    console.print(Align.center("[bold]Incode Benutzername[/bold]"))
    u = centered_input("[bold green]>[/bold green] ")
    
    console.print()
    console.print(Align.center("[bold]Passwort[/bold]"))
    p = centered_input("[bold green]>[/bold green] ", password=True)
    
    console.print()
    base_url = "https://dienstplan.k.roteskreuz.at" 
    extra_guids = None
    save_credentials(u, p, base_url, extra_guids, None)
    if not u or not p:
        sys.exit(0) # Exit if inputs are cancelled
    return u, p, base_url, extra_guids

def setup_auth(force_interactive=False):
    creds_data = load_credentials()
    users = creds_data.get('users', [])
    
    # 1. No users -> Create first one
    if not users:
        return _prompt_new_user()
    
    # 2. Single user and not forced -> Auto Login
    if len(users) == 1 and not force_interactive:
        u = users[0]
        # Status is printed in run_cli now to avoid duplication
        console.print(Align.center(f"Verwende gespeicherte Zugangsdaten für [info]{u['username']}[/info]"))
        return u['username'], u['password'], u.get('base_url'), u.get('extra_guids')

    # 3. Multiple users or forced -> Selection Menu
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print(Align.center("[bold]BENUTZER-AUSWAHL[/bold]"))
        console.print()
        
        options = []
        for user in users:
            options.append((f"Login als {user['username']}", user))
            
        options.append(("➕  Neuen Benutzer hinzufügen", "new"))
        options.append(("🗑️   Benutzer entfernen", "delete"))
        options.append(("🚪  Beenden", "exit"))
        
        selected = interactive_menu(options, title="LOGIN")
        
        if selected == "exit" or selected is None:
            sys.exit(0)
        elif selected == "new":
            return _prompt_new_user()
        elif selected == "delete":
            # Sub-menu for deletion
            del_options = [(f"Lösche {u['username']}", u['username']) for u in users]
            del_options.append(("Zurück", "back"))
            to_delete = interactive_menu(del_options, title="BENUTZER LÖSCHEN")
            if to_delete and to_delete != "back":
                remove_user(to_delete)
                # Reload users
                creds_data = load_credentials()
                users = creds_data.get('users', [])
                if not users: return _prompt_new_user()
        else:
            # User selected
            u = selected
            return u['username'], u['password'], u.get('base_url'), u.get('extra_guids')

def startup_checks(debug=False):
    # Check for updates
    try:
        from rich.spinner import Spinner
        from rich.live import Live
        if debug:
            console.print("[dim]Prüfe auf Updates (Debug mode)...[/dim]")
        
        with Live(Align.center(Spinner("dots", text="[dim]Prüfe auf Updates ...[/dim]")), console=console, transient=not debug):
            new_version = check_for_updates(debug=debug)
            
        if new_version:
            v_msg = f" (v{VERSION} -> v{new_version})" if new_version and new_version != "Neu" else ""
            console.print(Align.center(f"\n[bold yellow]✨ Ein Update ist verfügbar{v_msg}![/bold yellow]"))
            
            # from src.ui import prompt_yes_no # Redundant, already imported globally

            if prompt_yes_no("\nMöchtest du das Update jetzt automatisch installieren?"):
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
        elif debug:
             console.print("[dim]Debug: Keine Updates gefunden oder Check fertig.[/dim]")
             wait_for_return()
    except Exception as e:
        if debug:
            console.print(f"[red]Fehler bei startup_checks: {e}[/red]")
        pass # Ignore errors during update check to not block startup

def run_cli(debug=False):
    if not debug:
        clear_screen()
    console.print(Align.center(BANNER))
    startup_checks(debug=debug)
    
    force_menu = False
    
    while True:
        if not debug:
            clear_screen()
        console.print(Align.center(BANNER))
        
        u, p, base_url, extra_guids = setup_auth(force_interactive=force_menu)
        
        incode = IncodeRequests(base_url, extra_guids, username=u)
        
        status = get_storage_status(u)
        # Create a nice looking panel or text for the status
        from rich.panel import Panel
        
        status_color = "green" if "Verschlüsselt" in status else "yellow"
        console.print()
        console.print(Align.center(
            Panel.fit(
                f"[{status_color}]{status}[/{status_color}]",
                title="Sicherheits-Status",
                border_style="dim"
            )
        ))
        time.sleep(1.5) # Give user time to read
        
        s, m = incode.login(u, p)
        if not s: 
            console.print(Align.center(f"[error]{m}[/error]"))
            # If login failed, force menu next time to allow choosing another user or fixing credentials
            wait_for_return()
            force_menu = True
            continue
        
        # Save last active user on successful login
        update_credentials({}, username=u)
        
        # Pre-fetch next duty for dashboard
        next_duty = incode.get_next_duty()
        
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
            ("👤  Benutzer wechseln / Logout", "logout"),
            ("🚪  Beenden", "exit")
        ]

        should_logout = False
        while True:
            selection = interactive_menu(menu_options, dashboard_data=next_duty, current_user=u, allow_escape=False)
            
            if selection == "future":
                show_future_duties(incode)
                next_duty = incode.get_next_duty() # Refresh
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
                show_colleague_search(incode)
            elif selection == "live":
                show_live_monitor(incode)
            elif selection == "bot":
                start_bot_mode(incode)
            elif selection == "logout":
                should_logout = True
                force_menu = True
                break
            elif selection == "exit" or selection is None:
                clear_screen()
                console.print(Align.center("[dim]Auf Wiedersehen![/dim]"))
                sys.exit(0)
        
        if should_logout:
            continue

def start_bot_mode(incode_instance=None, debug=False):
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold blue]Starte Telegram Bot Modus ...[/bold blue]"))
    console.print()
    
    if not incode_instance:
        u, p, base_url, extra_guids = setup_auth()
        incode_instance = IncodeRequests(base_url, extra_guids, username=u)
    
    bot = IncodeBot(incode_instance)
    try:
        bot.run(debug=debug)
    except KeyboardInterrupt:
        console.print()
        console.print(Align.center("[bold yellow]Beende Telegram Bot... Bitte warten (nicht mehrmals klicken) ...[/bold yellow]"))
        # Allow some time or just let it exit naturally if possible, 
        # but usually KeyboardInterrupt stops the loop.
        # We catch it so we can print the message cleanly.
        pass

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
            run_cli(debug=debug_mode)
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer.")
