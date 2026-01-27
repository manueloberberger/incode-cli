
import json
import time
from typing import Dict, Any, List, Optional
from src.db import db
from src.config import console

def export_data(filepath: str) -> bool:
    """
    Exports all users and settings to a JSON file.
    Returns True on success, False on failure.
    """
    try:
        data = {
            'meta': {
                'version': 1,
                'timestamp': time.time(),
                'date_human': time.ctime()
            },
            'users': db.get_users(),
            'valuestore': db.get_all_values()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        return True
    except PermissionError:
        console.print(f"[bold red]Keine Schreibberechtigung für: {filepath}[/bold red]")
        return False
    except OSError as e:
        console.print(f"[bold red]Dateisystem-Fehler: {e}[/bold red]")
        return False
    except Exception as e:
        console.print(f"[bold red]Fehler beim Exportieren: {e}[/bold red]")
        return False

def import_data(filepath: str) -> bool:
    """
    Imports users and settings from a JSON file.
    Merges with existing data (upsert).
    Returns True on success, False on failure.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        users = data.get('users', [])
        valuestore = data.get('valuestore', {})
        
        # Import Users
        count_users = 0
        for u in users:
            # Safely extract fields with defaults
            username = u.get('username')
            if not username: continue
            
            db.upsert_user(
                username=username,
                password=u.get('password', ''),
                base_url=u.get('base_url', 'https://dienstplan.k.roteskreuz.at'),
                extra_guids=u.get('extra_guids', []),
                real_name=u.get('real_name'),
                telegram_token=u.get('telegram_token'),
                allowed_user_id=u.get('allowed_user_id')
            )
            count_users += 1
            
        # Import Settings
        count_settings = 0
        for key, value in valuestore.items():
            db.set_value(key, value)
            count_settings += 1
            
        console.print(f"[green]Import erfolgreich![/green]")
        console.print(f" - {count_users} Benutzer aktualisiert/erstellt")
        console.print(f" - {count_settings} Einstellungen wiederhergestellt")
        
        return True
        
    except FileNotFoundError:
        console.print(f"[bold red]Datei nicht gefunden: {filepath}[/bold red]")
        return False
    except json.JSONDecodeError:
        console.print(f"[bold red]Ungültiges Dateiformat (kein valides JSON): {filepath}[/bold red]")
        return False
    except Exception as e:
        console.print(f"[bold red]Fehler beim Importieren: {e}[/bold red]")
        return False
