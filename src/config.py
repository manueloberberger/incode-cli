import os
import json
import sys
from typing import Optional, Dict, List, Any
import keyring
from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt

# Custom Theme
theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "header": "bold magenta",
    "duty_beruflich": "green",
    "duty_ehrenamt": "cyan",
    "crew": "yellow",
    "stats": "bold blue",
    "live": "bold blink green"
})

console = Console(theme=theme)

VERSION = "2.4.10"

BANNER = rf"""
 [bold red]  ___ _  _  ___  ___  ___  ___       ___ _    ___   [/bold red] 
 [bold red] |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  [/bold red] 
 [bold white]  | || .  | (__| (_) | |) | _|     | (__| |__ | |   [/bold white] 
 [bold white] |___|_|\_|\___|\___/|___/|___|     \___|____|___|  [/bold white] 
 [bold white]                                                    [/bold white] 
 [bold white]                >> version {VERSION} <<                 [/bold white] 
"""

DEFAULT_TIMEOUT = 10 # seconds
CREDENTIALS_FILE = '.credentials.json'
BASE_URL_DEFAULT = "https://dienstplan.k.roteskreuz.at"
DEFAULT_GUID = None

def load_credentials(hydrate: bool = True) -> Dict[str, Any]:
    """
    Loads credentials.
    Returns a dict with structure: {'users': [user_dict, ...], 'last_active': str}
    Automatically migrates old format to new format and migrates plain text passwords to keyring.
    """
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                data = json.load(f)
            
            # Migration: Old format (root has username) -> New format (users list)
            if 'username' in data and 'users' not in data:
                # Convert old single user to list
                user = {
                    'username': data['username'],
                    'password': data['password'],
                    'base_url': data.get('base_url', BASE_URL_DEFAULT),
                    'extra_guids': data.get('extra_guids', []),
                    'real_name': data.get('real_name')
                }
                new_data = {
                    'users': [user],
                    'last_active': user['username']
                }
                # Save immediately to complete migration
                try:
                    with open(CREDENTIALS_FILE, 'w') as f:
                        json.dump(new_data, f, indent=4)
                except: pass
                # Re-assign data to proceed with processing
                data = new_data
            
            if 'users' not in data:
                data['users'] = []
    import sys
    debug = "--debug" in sys.argv
    
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
            
        users = data.get('users', [])
        changed = False
        
        # Check if migration needed (files with plain text passwords)
        for u in users:
            # 1. Migrate plain text password to keyring
            if u.get('password') and not u.get('password').startswith("KEYRING:"):
                try:
                    keyring.set_password("incode-cli", u['username'], u['password'])
                    u['password'] = None # Remove from file
                    changed = True
                    console.print(f"[green]Passwort für {u['username']} in sicherem Keyring migriert.[/green]")
                except Exception as e:
                    console.print(f"[warning]Konnte Passwort nicht migrieren: {e}[/warning]")

            # 2. Migrate plain text token to keyring
            if u.get('telegram_token') and not u.get('telegram_token').startswith("KEYRING:"):
                try:
                    keyring.set_password("incode-cli-telegram", u['username'], u['telegram_token'])
                    u['telegram_token'] = None # Remove from file
                    changed = True
                except Exception:
                    pass
        
        if changed:
            _write_credentials(data)
            
        # Hydrate passwords from Keyring if requested
        if hydrate:
            for u in users:
                # Password
                if u.get('password') is None:
                    try:
                        if debug: console.print(f"[dim]Debug: Lade Passwort für {u['username']} aus Keyring...[/dim]")
                        pw = keyring.get_password("incode-cli", u['username'])
                        if pw:
                            u['password'] = pw
                        elif debug: console.print(f"[dim]Debug: Kein Passwort im Keyring für {u['username']} gefunden.[/dim]")
                    except Exception as e:
                        if debug: console.print(f"[red]Debug: Keyring Fehler (Password): {e}[/red]")
                        console.print("[warning]Konnte Passwort nicht aus Keyring laden.[/warning]")
                
                # Token
                if u.get('telegram_token') is None:
                    try:
                        if debug: console.print(f"[dim]Debug: Lade Token für {u['username']} aus Keyring...[/dim]")
                        token = keyring.get_password("incode-cli-telegram", u['username'])
                        if token:
                            u['telegram_token'] = token
                    except Exception as e:
                        if debug: console.print(f"[red]Debug: Keyring Fehler (Token): {e}[/red]")
                        pass
                        
        return data
    except Exception as e:
        console.print(f"[error]Fehler beim Laden der Credentials: {e}[/error]")
        return {}
def save_credentials(username: str, password: str, base_url: str = BASE_URL_DEFAULT, extra_guids: Optional[List[str]] = None, real_name: Optional[str] = None) -> None:
    """
    Saves or updates a specific user.
    """
    if extra_guids is None:
        extra_guids = []
    
    data = load_credentials(hydrate=False)
    users = data.get('users', [])
    
    # Update existing or add new
    found = False
    
    # Save secret to keyring
    # Save secret to keyring
    keyring_success = False
    try:
        keyring.set_password("incode-cli", username, password)
        keyring_success = True
    except Exception as e:
        console.print(f"[warning]Keyring nicht verfügbar. Speichere Passwort lokal... ({e})[/warning]")

    for u in users:
        if u['username'] == username:
            if keyring_success:
                u['password'] = None # Securely stored
            else:
                u['password'] = password # Fallback
                
            u['base_url'] = base_url
            u['extra_guids'] = extra_guids
            u['real_name'] = real_name
            found = True
            break
    
    if not found:
        users.append({
            'username': username,
            'password': None if keyring_success else password,
            'base_url': base_url,
            'extra_guids': extra_guids,
            'real_name': real_name
        })
    
    data['users'] = users
    data['last_active'] = username
    
    _write_credentials(data)

def remove_user(username: str) -> None:
    data = load_credentials(hydrate=False)
    users = data.get('users', [])
    data['users'] = [u for u in users if u['username'] != username]
    
    if data.get('last_active') == username:
        data['last_active'] = data['users'][0]['username'] if data['users'] else None
        
    _write_credentials(data)
    
    # Remove from keyring
    try:
        keyring.delete_password("incode-cli", username)
        keyring.delete_password("incode-cli-telegram", username)
    except Exception:
        pass

def update_credentials(updates: Dict[str, Any], username: Optional[str] = None) -> None:
    """
    Updates specific fields for a user. If username is None, updates the last active user.
    """
    data = load_credentials(hydrate=False)
    target_user = username or data.get('last_active')
    
    if not target_user: return

    # Handle Keyring updates
    # Handle Keyring updates
    if 'password' in updates:
        try:
            keyring.set_password("incode-cli", target_user, updates['password'])
            updates['password'] = None # Don't save to file
        except Exception as e:
            console.print(f"[warning]Passwort konnte nicht in Keyring aktualisiert werden, speichere lokal: {e}[/warning]")
            # Keep password in updates, so it gets saved to file
            
    if 'telegram_token' in updates:
        try:
            keyring.set_password("incode-cli-telegram", target_user, updates['telegram_token'])
            updates['telegram_token'] = None
        except Exception as e:
            console.print(f"[warning]Telegram Token konnte nicht in Keyring aktualisiert werden, speichere lokal: {e}[/warning]")
            # Keep token in updates

    users = data.get('users', [])
    for u in users:
        if u['username'] == target_user:
            u.update(updates)
            break
    
    data['users'] = users
    _write_credentials(data)

def _write_credentials(data: Dict[str, Any]) -> None:
    """
    Writes credentials atomically to prevent data loss on crash.
    """
    import tempfile
    
    # Write to a temp file first
    try:
        # Create temp file in the same directory to ensure atomic move works
        dir_name = os.path.dirname(os.path.abspath(CREDENTIALS_FILE)) or '.'
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            json.dump(data, tf, indent=4)
            temp_name = tf.name
            
        # Permission set on temp file
        try:
            os.chmod(temp_name, 0o600)
        except Exception: pass
        
        # Atomic replacement
        os.replace(temp_name, CREDENTIALS_FILE)
        
    except Exception as e:
        console.print(f"[error]Fehler beim Speichern der Credentials: {e}[/error]")
        if 'temp_name' in locals() and os.path.exists(temp_name):
            try: os.remove(temp_name)
            except: pass

def get_storage_status(username: str) -> str:
    """
    Returns a string indicating where the password is stored for the given user.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return "❓ Unbekannt"
        
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
            users = data.get('users', [])
            for u in users:
                if u.get('username') == username:
                    if u.get('password'):
                        return "⚠️  Unverschlüsselt (Datei)"
                    else:
                        return "🔒 Verschlüsselt (Keyring)"
    except:
        pass
        
    return "❓ Unbekannt"