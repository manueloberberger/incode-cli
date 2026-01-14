import os
import json
import sys
from typing import Optional, Dict, List, Any
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

VERSION = "2.0.10"

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

def load_credentials() -> Dict[str, Any]:
    """
    Loads credentials.
    Returns a dict with structure: {'users': [user_dict, ...], 'last_active': str}
    Automatically migrates old format to new format.
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
                return new_data
            
            if 'users' not in data:
                data['users'] = []
            
            return data
            
        except Exception as e:
            console.print(f"[warning]Konnte Credentials nicht lesen: {e}[/warning]")
    return {'users': [], 'last_active': None}

def save_credentials(username: str, password: str, base_url: str = BASE_URL_DEFAULT, extra_guids: Optional[List[str]] = None, real_name: Optional[str] = None) -> None:
    """
    Saves or updates a specific user.
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

def _write_credentials(data: Dict[str, Any]) -> None:
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    try:
        os.chmod(CREDENTIALS_FILE, 0o600)
    except Exception: pass