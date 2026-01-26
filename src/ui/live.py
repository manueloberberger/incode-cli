"""
Live monitoring view for incode-cli.

This module provides real-time duty plan monitoring with auto-refresh
and optional Telegram notifications for changes.

Functions:
    show_live_monitor: Start the live monitoring mode
"""
from datetime import datetime
import time
import os
from typing import Any, Dict

from rich.align import Align
from rich.live import Live

from src.config import console, BANNER, load_credentials
from src.utils import clear_screen, get_key, centered_input, prompt_yes_no
from src.ui.components import interactive_menu, select_date_interactive, send_pdf_via_bot
# Circular import note: show_daily_plan is in src/ui/daily_plan.py
from src.ui.daily_plan import show_daily_plan
from src.pdf import export_to_pdf

def show_live_monitor(incode: Any) -> None:
    """
    Start the live duty plan monitoring mode.

    Continuously refreshes and displays the duty plan for a selected date.
    Optionally sends Telegram notifications when changes are detected.

    Args:
        incode: The IncodeRequests API instance.

    Features:
        - Auto-refresh every 60 seconds
        - Change detection with Telegram alerts
        - PDF export on changes (optional)
        - ESC to exit monitoring
    """
    # 1. Date Selection
    options = [("🕒  Heute überwachen", "today"), ("🗓️  Anderes Datum wählen", "date")]
    sel = interactive_menu(options, title="📺  LIVE MONITOR SETUP")
    if sel is None: return

    target_date = datetime.now()
    if sel == "date":
        d = select_date_interactive()
        if d: target_date = d
        else: return # Cancelled
    
    # 2. Telegram Setup
    enable_telegram = False
    
    # Check if configured
    creds = load_credentials()
    active_user = incode.username
    user_conf: Dict[str, Any] = next((u for u in creds.get('users', []) if u['username'] == active_user), {})
    has_telegram = user_conf.get("telegram_token") and user_conf.get("allowed_user_id")
    
    console.print() # Spacer
    if has_telegram:
        enable_telegram = prompt_yes_no("Telegram-Benachrichtigungen aktivieren (PDF bei Start & Änderung)?")
    else:
        console.print(Align.center("[dim]Telegram nicht konfiguriert - Benachrichtigungen deaktiviert.[/dim]"))
        time.sleep(1)
    
    # 3. Refresh Interval
    try:
        console.print() # Spacer
        console.print(Align.center("Aktualisierungs-Intervall (Minuten):"))
        min_str = centered_input("[bold green]>[/bold green] ", default="5")
        if min_str is None: # ESC
             return # Cancel monitor start
        refresh_interval = int(min_str) * 60
        if refresh_interval < 60: refresh_interval = 60
    except (ValueError, TypeError):
        refresh_interval = 300
    
    last_plan = None
    
    clear_screen()
    console.print(Align.center(BANNER))
    console.print(Align.center(f"[bold]Starte Monitor für {target_date.strftime('%d.%m.%Y')}...[/bold]"))
    console.print()
    
    first_run = True

    while True:
        try:
            # Load Data
            current_plan = incode.load_daily_plan(target_date)
            
            # Check for changes
            has_changes = False
            if last_plan is None:
                has_changes = True # First load is always a "change"
            else:
                if current_plan != last_plan:
                    has_changes = True

            if has_changes:
                last_plan = current_plan
                
                # Update UI
                show_daily_plan(incode, date=target_date, is_live=True, override_plan=current_plan)
                
                # Handle Notifications
                if enable_telegram and current_plan:
                    # Prepare export data (similar logic to show_daily_plan export)
                    export_duties = []
                    for p in current_plan:
                        try:
                            cl = []
                            for r in ["FAHRER", "SANITAETER1", "SANITAETER2"]:
                                if r in p["crew"]:
                                    cl.append(p['crew'][r])
                            export_duties.append({
                                'begin': p['begin'].strftime('%Y-%m-%dT%H:%M:%S'),
                                'end': p['end'].strftime('%Y-%m-%dT%H:%M:%S'),
                                'location': "", 'vehicle': p['vehicle'], 'duty_type': "", 'crew': cl
                            })
                        except (KeyError, AttributeError):
                            pass  # Skip malformed duty entries
                    
                    ts = datetime.now().strftime('%H:%M')
                    # Optimized filename for live updates
                    fn = f"Live_Tagesplan_{target_date.strftime('%Y-%m-%d')}_{datetime.now().strftime('%H-%M')}.pdf"
                    
                    if export_to_pdf(export_duties, fn):
                        msg_text = f"Live-Update für {target_date.strftime('%d.%m.%Y')} (Stand: {ts})"
                        if first_run:
                            msg_text = f"Live-Monitor gestartet für {target_date.strftime('%d.%m.%Y')} (Stand: {ts})"
                        
                        try:
                            console.print(Align.center(f"[dim]Sende Telegram Update...[/dim]"))
                            send_pdf_via_bot(incode, fn, msg_text)
                            console.print(Align.center(f"[success]Telegram gesendet.[/success]"))
                        except Exception as e:
                            console.print(Align.center(f"[error]Telegram Fehler: {e}[/error]"))
                        finally:
                            if os.path.exists(fn):
                                os.remove(fn)
            
            first_run = False
            
            # Countdown loop
            start_time = time.time()
            with Live(transient=True, console=console) as live:
                while time.time() - start_time < refresh_interval:
                    remaining = int(refresh_interval - (time.time() - start_time))
                    live.update(Align.center(f"[dim]Aktualisierung in {remaining}s. ESC zum Beenden ...[/dim]"))
                    
                    k = get_key(timeout=0.1)
                    if k == '\x1b' or (k and k.lower() == 'q'):
                        return

        except Exception as e:
            console.print(Align.center(f"[error]Fehler im Live-Monitor Loop: {e}[/error]"))
            # Wait a bit before retry to avoid spamming errors if network is down
            time.sleep(10)
