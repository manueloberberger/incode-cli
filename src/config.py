import os
import json
import sys
from typing import Optional, Dict, List, Any

from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt
from rich.align import Align

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

VERSION = "2.6.1"

BANNER = rf"""
[bold red]  ___ _  _  ___  ___  ___  ___       ___ _    ___   [/bold red]
[bold red] |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  [/bold red]
[bold white]  | || .  | (__| (_) | |) | _|     | (__| |__ | |   [/bold white]
[bold white] |___|_|\_|\___|\___/|___/|___|     \___|____|___|  [/bold white]

[bold white]                >> version {VERSION} <<                 [/bold white]
"""

DEFAULT_TIMEOUT = 10 # seconds
CREDENTIALS_FILE = '.credentials.json'
BASE_URL_DEFAULT = "https://dienstplan.k.roteskreuz.at"
DEFAULT_GUID = None

def load_credentials(hydrate: bool = True) -> Dict[str, Any]:
    """
    Loads credentials from the JSON file.
    Returns a dict with structure: {'users': [user_dict, ...], 'last_active': str}
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
            
        # Ensure 'users' list exists
        if 'users' not in data:
            data['users'] = []
            
        from typing import cast
        return cast(Dict[str, Any], data)
    except Exception as e:
        console.print(Align.center(f"[error]Fehler beim Laden der Credentials: {e}[/error]"))
        return {}

def save_credentials(username: str, password: str, base_url: str = BASE_URL_DEFAULT, extra_guids: Optional[List[str]] = None, real_name: Optional[str] = None) -> None:
    """
    Saves or updates a specific user to the JSON file.
    """
    if extra_guids is None:
        extra_guids = []
    
    data = load_credentials()
    users = data.get('users', [])
    
    # Update existing or add new
    found = False
    
    for u in users:
        if u['username'] == username:
            u['password'] = password
            u['base_url'] = base_url
            u['extra_guids'] = extra_guids
            u['real_name'] = real_name
            found = True
            break
    
    if not found:
        users.append({
            'username': username,
            'password': password,
            'base_url': base_url,
            'extra_guids': extra_guids,
            'real_name': real_name
        })
    
    data['users'] = users
    data['last_active'] = username
    
    _write_credentials(data)

def remove_user(username: str) -> None:
    data = load_credentials()
    users = data.get('users', [])
    data['users'] = [u for u in users if u['username'] != username]
    
    if data.get('last_active') == username:
        data['last_active'] = data['users'][0]['username'] if data['users'] else None
        
    _write_credentials(data)

def update_credentials(updates: Dict[str, Any], username: Optional[str] = None) -> None:
    """
    Updates specific fields for a user. If username is None, updates the last active user.
    """
    data = load_credentials()
    target_user = username or data.get('last_active')
    
    if not target_user: return

    users = data.get('users', [])
    for u in users:
        if u['username'] == target_user:
            u.update(updates)
            break
    
    data['users'] = users
    _write_credentials(data)

def get_update_interval() -> int:
    """Returns the update interval in seconds. Default: 21600 (6 hours)."""
    try:
        data = load_credentials()
        return int(data.get('update_interval', 21600))
    except:
        return 21600

def set_update_interval(seconds: int) -> None:
    """Saves the update interval in seconds."""
    try:
        data = load_credentials()
        data['update_interval'] = seconds
        _write_credentials(data)
    except:
        pass

def get_last_update_check() -> float:
    """Returns the timestamp of the last update check, or 0 if never checked."""
    try:
        data = load_credentials()
        return float(data.get('last_update_check', 0))
    except:
        return 0.0

def set_last_update_check(timestamp: float) -> None:
    """Saves the timestamp of the last update check."""
    try:
        data = load_credentials()
        data['last_update_check'] = timestamp
        _write_credentials(data)
    except:
        pass

def _write_credentials(data: Dict[str, Any]) -> None:
    """
    Writes credentials to JSON file atomically.
    """
    import tempfile
    
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
        console.print(Align.center(f"[error]Fehler beim Speichern der Credentials: {e}[/error]"))
        if 'temp_name' in locals() and os.path.exists(temp_name):
            try: os.remove(temp_name)
            except: pass

def get_storage_status(username: str) -> str:
    """
    Returns a string indicating where the password is stored.
    (Now always JSON/Portable)
    """
    return "✅ Lokal (JSON)"