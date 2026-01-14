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
        subprocess.run(["git", "fetch"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        
        # Check if behind upstream
        # HEAD..@{u} calculates commits reachable from upstream but not from HEAD
        res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..@{u}"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if res.returncode == 0 and res.stdout.strip().isdigit():
            count = int(res.stdout.strip())
            return count > 0
            
    except Exception:
        pass
        
    return False

def update_app() -> bool:
    """Performs safe git pull (with stash) and pip install. Returns True if successful."""
    try:
        console.print() # Initial Spacer
        
        # 1. Check for local changes
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        stashed = False
        
        if status:
            console.print(Align.center("[yellow]Lokale Änderungen erkannt. Sichere Arbeitsstand (git stash) ...[/yellow]"))
            subprocess.run(["git", "stash"], check=True, stdout=subprocess.DEVNULL)
            stashed = True
        
        # Capture current HEAD before pulling to check changes later
        current_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        
        # 2. Git Pull
        with Live(Align.center(Spinner("dots", text="[bold blue]Lade Updates von GitHub (git pull) ...[/bold blue]")), console=console, transient=True):
            subprocess.run(["git", "pull"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        console.print(Align.center("[dim]Updates heruntergeladen.[/dim]"))
        
        # 3. Restore Stash (if any)
        if stashed:
            console.print(Align.center("[info]Stelle lokale Änderungen wieder her (git stash pop) ...[/info]"))
            pop_res = subprocess.run(["git", "stash", "pop"], capture_output=True, text=True)
            if pop_res.returncode != 0:
                console.print(Align.center("[bold red]Warnung: Konflikte beim Wiederherstellen der Änderungen !!![/bold red]"))
                console.print(Align.center("Deine Änderungen sind im 'git stash' gespeichert."))
        
        # 4. Smart Dependency Check
        # Check if requirements.txt changed between old HEAD and new HEAD
        new_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        
        needs_pip = False
        if current_head != new_head:
            diff = subprocess.run(
                ["git", "diff", "--name-only", current_head, new_head], 
                capture_output=True, 
                text=True
            ).stdout
            if "requirements.txt" in diff:
                needs_pip = True
        
        console.print() # Spacer before dependency check output
        
        if needs_pip:
            with Live(Align.center(Spinner("dots", text="[bold blue]Aktualisiere Python-Abhängigkeiten (pip install) ...[/bold blue]")), console=console, transient=True):
                # Use sys.executable to ensure we use the same python/venv
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
            console.print(Align.center("[dim]Abhängigkeiten aktualisiert.[/dim]"))
        else:
            console.print(Align.center("[dim]Keine neuen Abhängigkeiten. Überspringe pip install.[/dim]"))
        
        console.print() # Spacer before success message
        console.print(Align.center("[success]Update erfolgreich abgeschlossen !!![/success]"))
        console.print() # Final Spacer
        return True
        
    except subprocess.CalledProcessError as e:
        console.print(Align.center(f"[error]Fehler beim Update-Prozess (Exit Code {e.returncode}).[/error]"))
        if e.stderr:
            console.print(Align.center(f"[dim]{e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr}[/dim]"))
        return False
    except Exception as e:
        console.print(Align.center(f"[error]Ein unerwarteter Fehler ist aufgetreten: {e}[/error]"))
        return False

from rich.align import Align
from rich.spinner import Spinner
from rich.live import Live
from rich.table import Table
from datetime import date, datetime, timedelta
from typing import List, Callable, TypeVar, Any
from functools import wraps
from requests import RequestException
from src.config import console

T = TypeVar("T")

def handle_api_errors(default_return: Any = None) -> Callable:
    """
    Decorator to handle API errors gracefully.
    Logs error to console and returns default_return.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except RequestException as e:
                console.print(Align.center(f"[dim red]Netzwerk-Fehler in {func.__name__}: {e}[/dim red]"))
            except Exception as e:
                console.print(Align.center(f"[dim red]Unerwarteter Fehler in {func.__name__}: {e}[/dim red]"))
            return default_return
        return wrapper
    return decorator

def get_holidays(year: int) -> List[date]:
    """Returns a list of Austrian holidays for the given year."""
    # Fixed
    holidays = [
        datetime(year, 1, 1).date(),
        datetime(year, 1, 6).date(),
        datetime(year, 5, 1).date(),
        datetime(year, 8, 15).date(),
        datetime(year, 10, 10).date(),
        datetime(year, 10, 26).date(),
        datetime(year, 11, 1).date(),
        datetime(year, 12, 8).date(),
        datetime(year, 12, 24).date(),
        datetime(year, 12, 25).date(),
        datetime(year, 12, 26).date(),
        datetime(year, 12, 31).date()
    ]
    
    # Variable (Easter based)
    a = year % 19; b = year // 100; c = year % 100
    d = b // 4; e = b % 4; f = (b + 8) // 25
    g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    dy = ((h + l - 7 * m + 114) % 31) + 1
    easter = datetime(year, mo, dy).date()
    
    # Ostersonntag (0), Ostermontag (+1), Himmelfahrt (+39), Pfingstsonntag (+49), Pfingstmontag (+50), Fronleichnam (+60)
    holidays.append(easter)                      # Easter Sunday
    holidays.append(easter + timedelta(days=1))  # Easter Monday
    holidays.append(easter + timedelta(days=39)) # Ascension
    holidays.append(easter + timedelta(days=49)) # Whit Sunday
    holidays.append(easter + timedelta(days=50)) # Whit Monday
    holidays.append(easter + timedelta(days=60)) # Corpus Christi
    
    return holidays


def wait_for_return() -> Optional[str]:
    console.print(Align.center("\n[bold dim]Beliebige Taste drücken um fortzufahren ...[/bold dim]"))

def prompt_yes_no(question: str) -> bool:
    """
    Shows an interactive Yes/No prompt with arrow navigation.
    Returns: True for Yes, False for No.
    """
    console.print(Align.center(f"{question}"))
    console.print()
    
    is_yes = True
    with Live(console=console, refresh_per_second=10) as live:
        while True:
            y_style = "[black on green]  Ja  [/]" if is_yes else "[dim]  Ja  [/dim]"
            n_style = "[black on green] Nein [/]" if not is_yes else "[dim] Nein [/dim]"
            
            grid = Table.grid(padding=(0, 4))
            grid.add_column(); grid.add_column()
            grid.add_row(y_style, n_style)
            
            live.update(Align.center(grid))
            
            k = get_key()
            if k == KEY_LEFT or k == KEY_LEFT_ALT or k == KEY_RIGHT or k == KEY_RIGHT_ALT:
                is_yes = not is_yes
            elif k == KEY_ENTER:
                return is_yes
            elif k == KEY_ESC or k == 'q':
                return False

def centered_input(label: str, password: bool = False, default: str = None) -> Optional[str]:
    """
    Reads input from user, centered. 
    Supports ESC to cancel (returns None).
    Supports Backspace.
    """
    console.print(Align.center(label), end="")
    sys.stdout.flush()
    
    input_str = ""
    
    while True:
        k = get_key()
        if not k: continue
        
        if k == KEY_ENTER:
            console.print() # Newline
            if not input_str and default:
                return default
            return input_str
            
        elif k == KEY_ESC:
            console.print() # Newline
            return None
            
        elif k == KEY_BACKSPACE or k == '\x7f' or k == '\b':
            if len(input_str) > 0:
                input_str = input_str[:-1]
                # Erase last char: Backspace, Space, Backspace
                sys.stdout.write('\b \b')
                sys.stdout.flush()
                
        elif len(k) == 1 and k.isprintable():
            input_str += k
            if password:
                sys.stdout.write('*')
            else:
                sys.stdout.write(k)
            sys.stdout.flush()
