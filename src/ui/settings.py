from src.config import console, BANNER, get_update_interval, set_update_interval, VERSION, update_credentials
from src.db import db

from src.ui.components import interactive_menu
from src.utils import clear_screen, check_for_updates, update_app, wait_for_return, prompt_yes_no, centered_input
import time
import sys
import os
from rich.align import Align
from typing import List, Tuple, Any, Dict, Optional

def show_settings_menu(current_user: Optional[str] = None) -> None:
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
            ("🔐  Passwort ändern", "password"),
            ("🤖  Telegram Konfiguration ändern", "telegram"),
            ("💾  Backup / Restore", "backup"),
            ("🔙  Zurück", "back")
        ]
        
        selected = interactive_menu(options, title="EINSTELLUNGEN")
        
        if selected == "back" or selected is None:
            break
        elif selected == "interval":
            _change_update_interval()
        elif selected == "check_now":
            _manual_update_check()
        elif selected == "password":
            _change_password(current_user)
        elif selected == "telegram":
            _change_telegram_config(current_user)
        elif selected == "backup":
            _backup_menu()

def _manual_update_check() -> None:
    from rich.live import Live
    from rich.spinner import Spinner
    
    console.print()
    with Live(Align.center(Spinner("dots", text="[bold blue]Prüfe auf Updates ...[/bold blue]")), console=console, transient=True):
        new_version = check_for_updates(ignore_cache=True)
    
    if new_version:
        console.print(Align.center(f"[bold red]✨ Update verfügbar: v{VERSION} -> v{new_version}[/bold red]\n"))
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
        time.sleep(1.2)

def _change_password(current_user: Optional[str] = None) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print(Align.center("[bold]PASSWORT ÄNDERN[/bold]\n"))
    
    active_user = current_user or db.get_active_user()
    if not active_user:
        console.print(Align.center("[red]Kein aktiver Benutzer![/red]"))
        wait_for_return()
        return

    user_data = db.get_user(active_user)
    current_pw = user_data.get('password', 'Unbekannt') if user_data else 'Unbekannt'
    
    console.print(Align.center(f"Aktuelles Passwort: [bold cyan]{current_pw}[/bold cyan]"))
    console.print(Align.center("[dim]Drücke ESC zum Abbrechen.[/dim]\n"))

    new_pw = centered_input("[bold green]Neues Passwort >[/bold green] ", password=True)
    if new_pw is None: # ESC pressed
        console.print(Align.center("\n[yellow]Abgebrochen.[/yellow]"))
        time.sleep(1)
        return

    if not new_pw:
        console.print(Align.center("\n[yellow]Abgebrochen (leeres Passwort).[/yellow]"))
        time.sleep(1)
        return
        
    confirm_pw = centered_input("[bold green]Wiederholen >[/bold green] ", password=True)
    if confirm_pw is None: # ESC pressed
        console.print(Align.center("\n[yellow]Abgebrochen.[/yellow]"))
        time.sleep(1)
        return

    if new_pw != confirm_pw:
        console.print(Align.center("\n[bold red]Passwörter stimmen nicht überein![/bold red]"))
        wait_for_return()
        return
        
        return
        
    update_credentials({'password': new_pw}, username=active_user)
    console.print(Align.center("\n[green]Passwort erfolgreich geändert![/green]"))
    time.sleep(1.5)

def _change_telegram_config(current_user: Optional[str] = None) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print(Align.center("[bold]TELEGRAM KONFIGURATION[/bold]\n"))
    
    active_user = current_user or db.get_active_user()
    if not active_user:
        console.print(Align.center("[red]Kein aktiver Benutzer![/red]"))
        wait_for_return()
        return

    user_data = db.get_user(active_user)
    if not user_data:
        console.print(Align.center("[red]Benutzerdaten nicht gefunden![/red]"))
        wait_for_return()
        return

    current_token = user_data.get('telegram_token') or "Nicht gesetzt"
    current_chat_id = user_data.get('allowed_user_id') or "Nicht gesetzt"
    
    # Display direct token (no masking as requested)
    masked_token = str(current_token)
        
    console.print(Align.center(f"Aktueller Token: [cyan]{masked_token}[/cyan]"))
    console.print(Align.center(f"Aktuelle Chat ID: [cyan]{current_chat_id}[/cyan]\n"))
    
    console.print(Align.center("[dim]Drücke Enter um den aktuellen Wert beizubehalten.[/dim]"))
    console.print(Align.center("[dim]Drücke ESC zum Abbrechen.[/dim]\n"))

    new_token = centered_input("[bold green]Neuer Bot Token >[/bold green] ")
    if new_token is None:
        return

    new_chat_id_str = centered_input("[bold green]Neue Chat ID >[/bold green] ")
    if new_chat_id_str is None:
        return
    
    updates: Dict[str, Any] = {}
    if new_token and new_token.strip():
        updates['telegram_token'] = new_token.strip()
    
    if new_chat_id_str and new_chat_id_str.strip():
        try:
            updates['allowed_user_id'] = int(new_chat_id_str.strip())
        except ValueError:
            console.print(Align.center("\n[red]Ungültige Chat ID! Muss eine Zahl sein.[/red]"))
            wait_for_return()
            return
        except ValueError:
            console.print(Align.center("\n[red]Ungültige Chat ID! Muss eine Zahl sein.[/red]"))
            wait_for_return()
            return
            
    if updates:
        update_credentials(updates, username=active_user)
        console.print(Align.center("\n[green]Telegram Konfiguration gespeichert![/green]"))
    else:
        console.print(Align.center("\n[yellow]Keine Änderungen vorgenommen.[/yellow]"))
        
        console.print(Align.center("\n[yellow]Keine Änderungen vorgenommen.[/yellow]"))
        
    time.sleep(1.5)

def _backup_menu() -> None:
    from src.backup import export_data, import_data
    
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print(Align.center("[bold]BACKUP / RESTORE[/bold]\n"))
        
        options = [
            ("💾  Backup erstellen (Export)", "export"),
            ("📥  Backup wiederherstellen (Import)", "import"),
            ("🔙  Zurück", "back")
        ]
        
        selection = interactive_menu(options, title="DATENSICHERUNG")
        
        if selection == "back" or selection is None:
            break
            
        elif selection == "export":
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            default_name = f"incode_backup_{timestamp}.json"
            
            console.print(Align.center(f"[dim]Standard-Dateiname: {default_name}[/dim]"))
            console.print(Align.center("[dim]Drücke Enter für Standard oder gib einen eigenen Namen ein.[/dim]\n"))
            
            filename = centered_input("[bold green]Dateiname >[/bold green] ")
            if filename is None: continue # Cancel
            
            final_name = filename.strip() if filename.strip() else default_name
            if not final_name.endswith(".json"):
                final_name += ".json"
                
            console.print()
            with console.status(f"[bold blue]Exportiere nach {final_name}...[/bold blue]"):
                success = export_data(final_name)
                
            if success:
                console.print(Align.center(f"\n[bold green]✅ Backup erfolgreich erstellt: {final_name}[/bold green]"))
            else:
                console.print(Align.center("\n[bold red]❌ Fehler beim Erstellen des Backups![/bold red]"))
            wait_for_return()
            
        elif selection == "import":
            console.print(Align.center("[dim]Gib den Dateinamen der Sicherung ein (z.B. incode_backup_2024....json)[/dim]\n"))
            
            filename = centered_input("[bold green]Dateiname >[/bold green] ")
            if not filename: continue
            
            console.print()
            if prompt_yes_no("Bist du sicher? Vorhandene Benutzer/Einstellungen werden überschrieben!"):
                with console.status(f"[bold blue]Importiere {filename}...[/bold blue]"):
                    success = import_data(filename)
                
                if success:
                    console.print(Align.center("\n[bold green]✅ Daten erfolgreich wiederhergestellt![/bold green]"))
                else:
                    console.print(Align.center("\n[bold red]❌ Fehler beim Import![/bold red]"))
                wait_for_return()
