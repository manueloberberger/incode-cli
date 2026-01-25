#!/usr/bin/env python3
import os
import sys
import time
import shutil
from datetime import datetime
from typing import Any, Tuple, Optional, List, Dict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rich.prompt import Prompt
from rich.console import Console
from rich.align import Align
from rich.table import Table
from rich.text import Text

try:
    from src.config import console, BANNER, load_credentials, save_credentials, update_credentials, remove_user, get_storage_status, VERSION
    from src.db import db
    # Import lightweight utils needed for basic UI/params
    from src.utils import clear_screen, centered_input, wait_for_return, get_key, KEY_LEFT, KEY_RIGHT, KEY_ENTER, KEY_LEFT_ALT, KEY_RIGHT_ALT
except ImportError as e:
    print(f"Fehler: Abhängigkeiten konnten nicht geladen werden ({e}).")
    print("Bitte führe 'pip install -r requirements.txt' aus.")
    sys.exit(1)

def _prompt_new_user() -> Tuple[str, str, str, Optional[List[str]]]:
    width = shutil.get_terminal_size().columns
    padding = (width // 2) - 4
    
    console.print()
    console.print(Align.center("[bold]Incode Benutzername[/bold]"))
    u = centered_input("[bold green]>[/bold green] ")
    
    console.print()
    console.print(Align.center("[bold]Passwort[/bold]"))
    p = centered_input("[bold green]>[/bold green] ", password=True)
    
    console.print()
    console.print(Align.center("[bold]Anzeigename (Optional)[/bold]"))
    real_name = centered_input("[bold green]>[/bold green] ")
    if not real_name or not real_name.strip(): real_name = None
    
    console.print()
    base_url = "https://dienstplan.k.roteskreuz.at" 
    extra_guids: Optional[List[str]] = None
    if not u or not p:
        sys.exit(0) # Exit if inputs are cancelled
    save_credentials(u, p, base_url, extra_guids, real_name)
    return u, p, base_url, extra_guids

def setup_auth(force_interactive: bool = False) -> Tuple[str, str, Optional[str], Optional[List[str]]]:
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
    from src.ui import interactive_menu
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print(Align.center("[bold]BENUTZER-AUSWAHL[/bold]"))
        console.print()
        
        options: List[Tuple[str, Any]] = []
        for user in users:
            display_str = f"👤  Login als {user['username']}"
            if user.get('real_name'):
                display_str += f" ({user['real_name']})"
            options.append((display_str, user))
            
        options.append(("➕  Neuen Benutzer hinzufügen", "new"))
        options.append(("✏️  Anzeigenamen ändern", "edit_alias"))
        options.append(("🗑️   Benutzer entfernen", "delete"))
        options.append(("🚪  Beenden", "exit"))
        
        selected = interactive_menu(options, title="LOGIN")
        
        if selected == "exit" or selected is None:
            sys.exit(0)
        elif selected == "new":
            return _prompt_new_user()
        elif selected == "delete":
            # Sub-menu for deletion
            del_options: List[Tuple[str, Any]] = [(f"🗑️  Lösche {u['username']}", u['username']) for u in users]
            del_options.append(("🔙  Zurück", "back"))
            to_delete = interactive_menu(del_options, title="BENUTZER LÖSCHEN")
            if to_delete and to_delete != "back":
                remove_user(to_delete)
                # Reload users
                creds_data = load_credentials()
                users = creds_data.get('users', [])
                if not users: return _prompt_new_user()
        elif selected == "edit_alias":
            # Sub-menu for editing alias
            edit_options: List[Tuple[str, Any]] = []
            for u in users:
                label = f"✏️  {u['username']}"
                if u.get('real_name'): label += f" ({u['real_name']})"
                edit_options.append((label, u))
            edit_options.append(("🔙  Zurück", "back"))
            
            target_u = interactive_menu(edit_options, title="ANZEIGENAMEN ÄNDERN")
            if target_u and target_u != "back":
                console.print()
                console.print(Align.center(f"[bold]Neuer Anzeigename für {target_u['username']}[/bold]"))
                console.print(Align.center("[dim](Leer lassen um zu löschen)[/dim]"))
                console.print()
                new_alias = centered_input("[bold green]>[/bold green] ")
                if new_alias is None: continue
                final_alias = new_alias.strip() if new_alias.strip() else None
                
                update_credentials({'real_name': final_alias}, username=target_u['username'])
                # Reload users loop
                creds_data = load_credentials()
                users = creds_data.get('users', [])
        else:
            # User selected
            u = selected
            return u['username'], u['password'], u.get('base_url'), u.get('extra_guids')

def startup_checks(debug: bool = False) -> None:
    # Check for updates
    try:
        from rich.spinner import Spinner
        from rich.live import Live
        from src.utils import check_for_updates, update_app, prompt_yes_no
        if debug:
            console.print("[dim]Prüfe auf Updates (Debug mode)...[/dim]")
        
        with Live(Align.center(Spinner("dots", text="[dim]Prüfe auf Updates ...[/dim]")), console=console, transient=not debug):
            new_version = check_for_updates(debug=debug)
            
        if new_version:
            v_msg = f" (v{VERSION} -> v{new_version})" if new_version and new_version != "Neu" else ""
            console.print(Align.center(f"\n[bold red]✨ Ein Update ist verfügbar{v_msg}![/bold red]"))
            
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

def run_cli(debug: bool = False) -> None:
    if not debug:
        clear_screen()
    console.print(Align.center(BANNER))
    startup_checks(debug=debug)
    
    from src.api import IncodeRequests
    from src.ui import show_future_duties, show_daily_plan, show_live_monitor, interactive_menu, select_date_interactive, show_staff_search, show_absences, show_events_menu, show_colleague_search, show_settings_menu
    from src.ui.list_view import show_plan_list
    from src.utils import prompt_yes_no
    from rich.live import Live
    from rich.spinner import Spinner
    
    force_menu = False
    
    while True:
        if not debug:
            clear_screen()
        console.print(Align.center(BANNER))
        
        if debug: console.print("[dim]Debug: Calling setup_auth...[/dim]")
        u, p, base_url, extra_guids = setup_auth(force_interactive=force_menu)
        if debug: console.print(f"[dim]Debug: setup_auth returned user: {u}[/dim]")
        
        incode = IncodeRequests(base_url or "https://dienstplan.k.roteskreuz.at", extra_guids, username=u)
        
        # Status display removed as per user request
        
        from src.exceptions import LoginError, IncodeError
        try:
            with Live(Align.center(Spinner("dots", text=f" Melde an als {u} ...")), console=console, transient=True):
                incode.login(u, p)
            # time.sleep(1) # Removing artificial delay
        except LoginError as e:
            console.print(Align.center(f"[error]{e}[/error]"))
            # If login failed, force menu next time to allow choosing another user or fixing credentials
            wait_for_return()
            force_menu = True
            continue
        except Exception as e:
            console.print(Align.center(f"[error]Unerwarteter Fehler: {e}[/error]"))
            wait_for_return()
            force_menu = True
            continue
        
        # Save last active user on successful login
        # Try to fetch real name if missing
        # We need to check if we already have a real name saved
        from src.config import load_credentials
        current_creds = load_credentials().get('users', [])
        current_user_obj: Dict[str, Any] = next((user for user in current_creds if user['username'] == u), {})
        real_name = current_user_obj.get('real_name')
        
        if not real_name:
            try:
                # Need to use the API to find the name
                fetched_name = incode.get_user_name(u)
                if fetched_name:
                    real_name = fetched_name
                    # Update immediately in config
                    update_credentials({'real_name': real_name}, username=u)
            except: pass

        update_credentials({}, username=u)
        db.set_active_user(u)
        
        # Pre-fetch next duty for dashboard
        next_duty = incode.get_next_duty()
        
        menu_options: List[Tuple[str, Any]] = [
            ("📅  Mein Dienstplan", "future"),
            ("🌴  Meine Abwesenheiten", "absences"),
            ("🚑  Events / Ambulanzdienste", "events"),
            ("🚑  Tagesplan (Heute)", "today"),
            ("📆  Tagesplan (Datum wählen)", "date"),
            ("📋  Tagespläne (Liste)", "list_view"),
            ("📒  Mitarbeiter-Verzeichnis", "staff"),
            ("🔍  Gemeinsame Dienste suchen", "colleague"),
            ("📺  Live-Monitor", "live"),
            ("🤖  Telegram Bot", "bot"),
            ("⚙️   Einstellungen", "settings"),
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
            elif selection == "list_view":
                show_plan_list(incode)
            elif selection == "staff":
                show_staff_search(incode)
            elif selection == "colleague":
                show_colleague_search(incode)
            elif selection == "live":
                show_live_monitor(incode)
            elif selection == "bot":
                show_bot_menu(incode)
            elif selection == "settings":
                show_settings_menu(u)
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

def show_bot_menu(incode_instance: Any) -> None:
    """Show unified bot menu with interactive start and service management."""
    from src.ui import interactive_menu
    from src.service import install_service, uninstall_service, check_service_status, has_installed_services
    from src.utils import wait_for_return
    
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print()
        
        # Check if services are installed
        services_exist = has_installed_services()
        
        options: List[Tuple[str, Any]] = [
            ("▶️  Bot jetzt starten (interaktiv)", "start"),
            ("🟢  Als Systemdienst installieren", "install"),
        ]
        
        if services_exist:
            options.append(("🔴  Systemdienst deinstallieren", "uninstall"))
        
        options.extend([
            ("📊  Systemdienst Status anzeigen", "status"),
            ("🔙  Zurück zum Hauptmenü", "back")
        ])
        
        selection = interactive_menu(options, title="TELEGRAM BOT")
        
        if selection == "start":
            start_bot_mode(incode_instance)
        elif selection == "install":
            install_service()
            wait_for_return()
        elif selection == "uninstall":
            uninstall_service()
            wait_for_return()
        elif selection == "status":
            check_service_status()
            wait_for_return()
        elif selection == "back" or selection is None:
            break

def start_bot_mode(incode_instance: Any = None, debug: bool = False, specific_user: Optional[str] = None, force_menu: bool = False) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold blue]Starte Telegram Bot Modus ...[/bold blue]"))
    console.print()
    
    if not incode_instance:
        u = None
        # Valid logic:
        # 1. If --user passed, try to find that user
        # 2. If --select passed, force setup_auth
        # 3. Else try auto-login with last active
        
        from src.config import load_credentials
        creds = load_credentials()
        users = creds.get('users', [])
        
        target_user = None
        
        if force_menu:
             # Force interactive
             pass
        elif specific_user:
             target_user = next((u for u in users if u['username'].lower() == specific_user.lower() or (u.get('real_name') and specific_user.lower() in u['real_name'].lower())), None)
             if not target_user:
                 console.print(Align.center(f"[red]Benutzer '{specific_user}' nicht gefunden.[/red]"))
                 sys.exit(1)
        else:
             # Auto-login default
            last_active = creds.get('last_active')
            target_user = next((u for u in users if u['username'] == last_active), None)
        
        if target_user and not force_menu:
            u = target_user['username']
            p = target_user['password']
            base_url = target_user.get('base_url')
            extra_guids = target_user.get('extra_guids')
            console.print(Align.center(f"[dim]Auto-Login als {u}[/dim]"))
            
            from src.api import IncodeRequests
            incode_instance = IncodeRequests(base_url or "https://dienstplan.k.roteskreuz.at", extra_guids, username=u)
            # Ensure we update last_active so next run uses this one too
            update_credentials({}, username=u)
        else:
            # Fallback to menu if no last active user found OR forced
            u, p, base_url, extra_guids = setup_auth(force_interactive=True) # Force menu if we land here
            from src.api import IncodeRequests
            incode_instance = IncodeRequests(base_url or "https://dienstplan.k.roteskreuz.at", extra_guids, username=u)
    
    from src.bot import IncodeBot
    bot = IncodeBot(incode_instance)
    try:
        bot.run(debug=debug)
    except KeyboardInterrupt:
        console.print()
        console.print(Align.center("[bold yellow]Beende Telegram Bot... Bitte warten (nicht mehrmals klicken) ...[/bold yellow]"))
        pass

def show_help() -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold cyan]Incode CLI - Hilfesystem[/bold cyan]"))
    console.print()
    
    help_text = [
        ("Befehl", "Beschreibung"),
        ("---", "---"),
        ("./incode", "Startet das interaktive Hauptmenü (Standard)."),
        ("./incode bot", "Startet den Telegram Bot Modus (Auto-Login)."),
        ("./incode bot --debug", "Startet den Bot mit erweiterten technischen Logs."),
        ("./incode bot --select", "Startet den Bot mit Benutzer-Auswahlmenü."),
        ("./incode bot --user <NAME>", "Startet den Bot für einen spezifischen Benutzer (User/Name)."),
        ("./incode install-service", "Installiert den Bot als Systemdienst (Linux/systemd)."),
        ("./incode --no-keyring", "Zwingt die Nutzung der Datei anstatt des System-Keyrings (für Linux/Kali)."),
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
        force_select = "--select" in sys.argv
        
        specific_user = None
        if "--user" in sys.argv:
            try:
                idx = sys.argv.index("--user")
                if idx + 1 < len(sys.argv):
                    specific_user = sys.argv[idx + 1]
            except: pass

        if len(sys.argv) > 1 and "install-service" in sys.argv:
            from src.service import install_service
            
            # Check for --user argument
            service_user = None
            if "--user" in sys.argv:
                try:
                    idx = sys.argv.index("--user")
                    if idx + 1 < len(sys.argv):
                        service_user = sys.argv[idx + 1]
                except: pass
            
            install_service(specific_user=service_user)
        elif len(sys.argv) > 1 and "bot" in sys.argv:
            start_bot_mode(debug=debug_mode, specific_user=specific_user, force_menu=force_select)
        else:
            run_cli(debug=debug_mode)
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer.")
