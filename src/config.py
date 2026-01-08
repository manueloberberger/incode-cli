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

VERSION = "1.8.5"

BANNER = rf"""
 [bold red]  ___ _  _  ___  ___  ___  ___       ___ _    ___   [/bold red] 
 [bold red] |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  [/bold red] 
 [bold white]  | || .  | (__| (_) | |) | _|     | (__| |__ | |   [/bold white] 
 [bold white] |___|_|\_|\___|\___/|___/|___|     \___|____|___|  [/bold white] 
 [bold white]                                                    [/bold white] 
 [bold white]                  >> version {VERSION} <<                  [/bold white] 
"""

DEFAULT_TIMEOUT = 10 # seconds
CREDENTIALS_FILE = '.credentials.json'
BASE_URL_DEFAULT = "https://dienstplan.k.roteskreuz.at"
DEFAULT_GUID = '0612f4321d9f3bb974db663770e9e1a01593a377_2_1702968855_1605'

def load_credentials() -> Optional[Dict[str, Any]]:
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[warning]Konnte Credentials nicht lesen: {e}[/warning]")
    return None

def save_credentials(username: str, password: str, base_url: str = BASE_URL_DEFAULT, extra_guids: Optional[List[str]] = None, real_name: Optional[str] = None) -> None:
    if extra_guids is None:
        extra_guids = [DEFAULT_GUID]
    
    data = {
        'username': username,
        'password': password,
        'base_url': base_url,
        'extra_guids': extra_guids,
        'real_name': real_name
    }
    
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    
    try:
        os.chmod(CREDENTIALS_FILE, 0o600)
    except Exception as e:
        console.print(f"[warning]Konnte Dateirechte für {CREDENTIALS_FILE} nicht setzen: {e}[/warning]")

def update_credentials(updates: Dict[str, Any]) -> None:
    data = load_credentials() or {}
    data.update(updates)
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    try:
        os.chmod(CREDENTIALS_FILE, 0o600)
    except Exception: pass