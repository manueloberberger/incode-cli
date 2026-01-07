import os
import sys
import time
import select
from typing import Optional, Any
from requests.adapters import HTTPAdapter
from src.config import DEFAULT_TIMEOUT, console

# Platform specific imports
if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios
    import fcntl

# Key Constants
KEY_UP = '\x1b[A'
KEY_DOWN = '\x1b[B'
KEY_RIGHT = '\x1b[C'
KEY_LEFT = '\x1b[D'
KEY_UP_ALT = '\x1bOA'
KEY_DOWN_ALT = '\x1bOB'
KEY_RIGHT_ALT = '\x1bOC'
KEY_LEFT_ALT = '\x1bOD'
KEY_ENTER = '\r'
KEY_ESC = '\x1b'
KEY_BACKSPACE = '\x7f'

class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request: Any, **kwargs: Any) -> Any:
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)

def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')

def flush_input() -> None:
    """Clears the input buffer."""
    if os.name == 'nt':
        while msvcrt.kbhit():
            msvcrt.getch()
    else:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)

def get_key(timeout: Optional[float] = None) -> Optional[str]:
    """
    Reads a keypress. Handles platform differences.
    timeout: Seconds to wait. None = block indefinitely (or until key).
    Returns key sequence or None if timeout.
    """
    if os.name == 'nt':
        return _get_key_windows(timeout)
    else:
        return _get_key_unix(timeout)

def _get_key_windows(timeout: Optional[float]) -> Optional[str]:
    # If timeout is None, block
    if timeout is None:
        # msvcrt.getch() blocks
        return _read_windows_key_blocking()
    
    # If timeout specified, poll
    start = time.time()
    while True:
        if msvcrt.kbhit():
            return _read_windows_key_blocking()
        if time.time() - start > timeout:
            return None
        time.sleep(0.01)

def _read_windows_key_blocking() -> Optional[str]:
    ch = msvcrt.getch()
    # Handle special keys
    if ch == b'\x00' or ch == b'\xe0':
        sc = msvcrt.getch()
        if sc == b'H': return KEY_UP
        if sc == b'P': return KEY_DOWN
        if sc == b'K': return KEY_LEFT
        if sc == b'M': return KEY_RIGHT
        return None
        
    if ch == b'\r': return KEY_ENTER
    if ch == b'\x1b': return KEY_ESC
    if ch == b'\x08': return KEY_BACKSPACE
    
    try:
        return ch.decode('utf-8')
    except:
        return None

def _get_key_unix(timeout: Optional[float]) -> Optional[str]:
    """
    Reads a keypress using low-level os.read and select.
    """
    fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(fd)
    except termios.error:
        return None

    try:
        tty.setraw(fd)
        
        # Check if data is available
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            return None # Timeout
        
        ch = os.read(fd, 1)
        
        if ch == b'\x1b':
            # We got ESC, now check if there are more chars (sequence)
            # Make fd non-blocking temporarily for the sequence
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            seq = ch
            try:
                # Give a tiny window for the sequence to arrive
                time.sleep(0.01) 
                while len(seq) < 5:
                    try:
                        next_char = os.read(fd, 1)
                        if not next_char: break
                        seq += next_char
                    except OSError:
                        break
            finally:
                fcntl.fcntl(fd, fcntl.F_SETFL, fl)
            
            return seq.decode('utf-8', errors='ignore')
            
        return ch.decode('utf-8', errors='ignore')

    except Exception:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

import subprocess

def check_for_updates() -> bool:
    """Checks for git updates. Returns True if updates are available."""
    if not os.path.exists(".git"):
        return False
    
    try:
        # Fetch latest changes silently (timeout to prevent hanging)
        subprocess.run(["git", "fetch"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        
        # Check if behind upstream
        # HEAD..@{u} calculates commits reachable from upstream but not from HEAD
        res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..@{u}"], 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        
        if res.returncode == 0 and res.stdout.strip().isdigit():
            count = int(res.stdout.strip())
            return count > 0
            
    except Exception:
        pass
        
    return False

def update_app() -> bool:
    """Performs git pull and pip install. Returns True if successful."""
    try:
        console.print("[info]Führe 'git pull' aus...[/info]")
        subprocess.run(["git", "pull"], check=True)
        
        console.print("[info]Aktualisiere Abhängigkeiten (pip install)...[/info]")
        # Use sys.executable to ensure we use the same python/venv
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        
        console.print("[success]Update erfolgreich abgeschlossen![/success]")
        return True
    except Exception as e:
        console.print(f"[error]Update fehlgeschlagen: {e}[/error]")
        return False

def wait_for_return() -> Optional[str]:
    console.print("\n[dim]Beliebige Taste drücken um fortzufahren...[/dim]")
    flush_input()
    while True:
        k = get_key()
        if k: return k
