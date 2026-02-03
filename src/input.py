"""
Input handling module for incode-cli.
Contains keyboard input, terminal I/O, and user prompts.
"""
import logging
import os
import sys
import time
import select
import shutil
import re
from typing import Optional

logger = logging.getLogger(__name__)

from rich.align import Align
from rich.table import Table
from rich.live import Live

from src.config import KEY_POLL_INTERVAL, console

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


def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def flush_input() -> None:
    """Clears the input buffer."""
    if os.name == 'nt':
        while msvcrt.kbhit():  # type: ignore
            msvcrt.getch()  # type: ignore
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
        if msvcrt.kbhit():  # type: ignore
            return _read_windows_key_blocking()
        if time.time() - start > timeout:
            return None
        time.sleep(KEY_POLL_INTERVAL)


def _read_windows_key_blocking() -> Optional[str]:
    ch = msvcrt.getch()  # type: ignore
    # Handle special keys
    if ch == b'\x00' or ch == b'\xe0':
        sc = msvcrt.getch()  # type: ignore
        if sc == b'H': return KEY_UP
        if sc == b'P': return KEY_DOWN
        if sc == b'K': return KEY_LEFT
        if sc == b'M': return KEY_RIGHT
        return None
        
    if ch == b'\r': return KEY_ENTER
    if ch == b'\x1b': return KEY_ESC
    if ch == b'\x08': return KEY_BACKSPACE
    
    try:
        if isinstance(ch, bytes):
            return ch.decode('utf-8')
        return None
    except (UnicodeDecodeError, AttributeError):
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
        # Use TCSADRAIN to prevent flushing input buffer (defaults to TCSAFLUSH)
        # preventing lost keys during sleep periods
        tty.setraw(fd, termios.TCSADRAIN)
        
        # Check if data is available
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            return None  # Timeout
        
        ch = os.read(fd, 1)
        
        if ch == b'\x1b':
            # We got ESC, now check if there are more chars (sequence)
            # Make fd non-blocking temporarily for the sequence
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            seq = ch
            try:
                # Give a tiny window for the sequence to arrive
                time.sleep(KEY_POLL_INTERVAL) 
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

    except (OSError, termios.error) as e:
        logger.debug(f"Terminal input error: {e}")
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def unicode_len(s: str) -> int:
    """Helper to get visual length of string ignoring ANSI codes for centering calculation."""
    # Strip ANSI codes for length calculation
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return len(ansi_escape.sub('', s))


def wait_for_return() -> Optional[str]:
    console.print(Align.center("\n[bold dim]Beliebige Taste drücken um fortzufahren ...[/bold dim]"))
    flush_input()
    while True:
        k = get_key()
        if k: return k


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


def centered_input(label: str, password: bool = False, default: Optional[str] = None) -> Optional[str]:
    """
    Reads input from user, centered. 
    Supports ESC to cancel (returns None).
    Supports Backspace.
    """
    # Calculate padding to center the label
    width = shutil.get_terminal_size().columns
    # Ensure non-negative padding
    padding = max(0, (width // 2) - unicode_len(label))
    
    # Print the label with padding
    console.print(" " * padding + label, end="")
    sys.stdout.flush()
    
    input_str = ""
    
    while True:
        k = get_key()
        if not k: continue
        
        if k == KEY_ENTER:
            console.print()  # Newline
            if not input_str and default:
                return default
            return input_str
            
        elif k == KEY_ESC:
            console.print()  # Newline
            return None
            
        elif k in (KEY_BACKSPACE, '\b'):  # KEY_BACKSPACE is '\x7f', '\b' is '\x08'
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
