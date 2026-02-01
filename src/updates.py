"""
Update handling module for incode-cli.
Contains update checking and application update logic.
"""
import os
import sys
import time
import subprocess
import re
from typing import Optional

from rich.align import Align
from rich.spinner import Spinner
from rich.live import Live

from src.config import (
    console, 
    get_last_update_check, 
    set_last_update_check, 
    get_update_interval,
    GIT_FETCH_TIMEOUT, 
    GIT_REVLIST_TIMEOUT, 
    GIT_SHOW_TIMEOUT
)


def check_for_updates(debug: bool = False, ignore_cache: bool = False) -> Optional[str]:
    """Checks for git updates. Returns new version string if updates are available, else None."""
    if not os.path.exists(".git"):
        if debug: console.print("[yellow]Debug: Keine .git Directory gefunden.[/yellow]")
        return None
    
    # Check cache
    if not debug and not ignore_cache:
        last_check = get_last_update_check()
        interval = get_update_interval()
        if time.time() - last_check < interval:
            return None

    try:
        # Fetch latest changes silently (timeout to prevent hanging)
        if debug: console.print("[dim]Debug: Running git fetch...[/dim]")
        subprocess.run(["git", "fetch"], check=True, stdout=subprocess.DEVNULL if not debug else None, stderr=subprocess.DEVNULL if not debug else None, timeout=GIT_FETCH_TIMEOUT)
        
        # Check if behind upstream
        # HEAD..@{u} calculates commits reachable from upstream but not from HEAD
        if debug: console.print("[dim]Debug: Checking rev-list...[/dim]")
        res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..@{u}"], 
            capture_output=True, 
            text=True, 
            timeout=GIT_REVLIST_TIMEOUT
        )
        
        if res.returncode == 0 and res.stdout.strip().isdigit():
            count = int(res.stdout.strip())
            if debug: console.print(f"[dim]Debug: Commits behind: {count}[/dim]")
            
            if count > 0:
                # Try to get remote version
                try:
                    ver_res = subprocess.run(
                        ["git", "show", "@{u}:src/config.py"], 
                        capture_output=True, 
                        text=True, 
                        timeout=GIT_SHOW_TIMEOUT
                    )
                    if ver_res.returncode == 0:
                        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', ver_res.stdout)
                        if match:
                            return match.group(1)
                except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                    pass
                return "Neu"  # Fallback if version extraction fails but update exists
        elif debug:
            console.print(f"[yellow]Debug: git rev-list failed: {res.stderr}[/yellow]")
            
    except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError) as e:
        if debug: console.print(f"[red]Debug: Update check error: {e}[/red]")
    
    # Update timestamp if we actually checked (successfully or not, to avoid spamming on error)
    if not debug:
        set_last_update_check(time.time())
        
    return None


def update_app() -> bool:
    """Performs safe git pull (with stash) and pip install. Returns True if successful."""
    try:
        console.print()  # Initial Spacer
        
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
        
        console.print()  # Spacer before dependency check output
        
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
        
        # 5. Restart Services (if any)
        try:
            # Local import to avoid circular dependency
            from src.service import restart_services
            restart_services()
        except Exception as e:
            # Don't fail the update just because service restart failed
            console.print(Align.center(f"[yellow]Warnung: Konnte Services nicht neustarten ({e})[/yellow]"))

        
        console.print()  # Spacer before success message
        console.print(Align.center("[success]Update erfolgreich abgeschlossen !!![/success]"))
        console.print()  # Final Spacer
        return True
        
    except subprocess.CalledProcessError as e:
        console.print(Align.center(f"[error]Fehler beim Update-Prozess (Exit Code {e.returncode}).[/error]"))
        if e.stderr:
            console.print(Align.center(f"[dim]{e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr}[/dim]"))
        return False
    except Exception as e:
        console.print(Align.center(f"[error]Ein unerwarteter Fehler ist aufgetreten: {e}[/error]"))
        return False
