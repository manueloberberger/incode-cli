import os
import sys
from typing import Optional, Dict, List, Any

import logging
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt
from rich.align import Align

from src.db import db

# Setup Logging
def setup_logging(verbose: bool = False) -> None:
    """Configures application-wide logging to file."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Log to incode.log in the current directory
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler("incode.log", maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
        ]
    )
    # Silence noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

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

VERSION = "2.16.2"

BANNER = rf"""
[bold red]  ___ _  _  ___  ___  ___  ___       ___ _    ___   [/bold red]
[bold red] |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  [/bold red]
[bold white]  | || .  | (__| (_) | |) | _|     | (__| |__ | |   [/bold white]
[bold white] |___|_|\_|\___|\___/|___/|___|     \___|____|___|  [/bold white]

[bold white]                >> version {VERSION} <<                 [/bold white]
"""

# Timeout Constants (seconds)
DEFAULT_TIMEOUT = 10
GIT_FETCH_TIMEOUT = 10
GIT_REVLIST_TIMEOUT = 5
GIT_SHOW_TIMEOUT = 5

# Terminal I/O
KEY_POLL_INTERVAL = 0.01

BASE_URL_DEFAULT = "https://dienstplan.k.roteskreuz.at"

def load_credentials(hydrate: bool = True) -> Dict[str, Any]:
    """
    Loads credentials from the Database.
    Returns a dict with structure: {'users': [user_dict, ...], 'last_active': str}
    Compatible with old JSON structure for API consumers.
    """
    users = db.get_users()
    last_active = db.get_active_user()
    
    return {
        'users': users,
        'last_active': last_active
    }

def save_credentials(username: str, password: str, base_url: str = BASE_URL_DEFAULT, extra_guids: Optional[List[str]] = None, real_name: Optional[str] = None, telegram_token: Optional[str] = None, allowed_user_id: Optional[int] = None) -> None:
    """
    Saves or updates a specific user to the DB.
    """
    if extra_guids is None:
        extra_guids = []
    
    db.upsert_user(
        username=username,
        password=password,
        base_url=base_url,
        extra_guids=extra_guids,
        real_name=real_name,
        telegram_token=telegram_token,
        allowed_user_id=allowed_user_id
    )
    db.set_active_user(username)

def remove_user(username: str) -> None:
    db.remove_user(username)
    
    # Check if we need to update last_active
    current_active = db.get_active_user()
    if current_active == username:
        users = db.get_users()
        if users:
            db.set_active_user(users[0]['username'])
        else:
            db.set_value("last_active_user", None)

def update_credentials(updates: Dict[str, Any], username: Optional[str] = None) -> None:
    """
    Updates specific fields for a user. If username is None, updates the last active user.
    """
    target_user = username or db.get_active_user()
    if not target_user: return

    user = db.get_user(target_user)
    if not user: return

    # Merge updates
    new_user = {**user, **updates}
    
    # Safe cast back to argument types
    db.upsert_user(
        username=new_user['username'],
        password=new_user['password'],
        base_url=new_user.get('base_url', BASE_URL_DEFAULT),
        extra_guids=new_user.get('extra_guids', []),
        real_name=new_user.get('real_name'),
        telegram_token=new_user.get('telegram_token'),
        allowed_user_id=new_user.get('allowed_user_id')
    )

def get_update_interval() -> int:
    """Returns the update interval in seconds. Default: 21600 (6 hours)."""
    return int(db.get_value('update_interval', 21600))

def set_update_interval(seconds: int) -> None:
    """Saves the update interval in seconds."""
    db.set_value('update_interval', seconds)

def get_last_update_check() -> float:
    """Returns the timestamp of the last update check, or 0 if never checked."""
    return float(db.get_value('last_update_check', 0))

def set_last_update_check(timestamp: float) -> None:
    """Saves the timestamp of the last update check."""
    db.set_value('last_update_check', timestamp)

def get_storage_status(username: str) -> str:
    """
    Returns a string indicating where the password is stored.
    """
    return "SQLite"