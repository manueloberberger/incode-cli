import calendar
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Any

from rich.table import Table
from rich.align import Align
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from src.config import console, BANNER, load_credentials, get_storage_status
from src.utils import clear_screen, get_key, KEY_UP, KEY_UP_ALT, KEY_DOWN, KEY_DOWN_ALT, KEY_ENTER, KEY_ESC, KEY_LEFT, KEY_LEFT_ALT, KEY_RIGHT, KEY_RIGHT_ALT
from src.bot import IncodeBot

def send_pdf_via_bot(incode_instance: Any, file_path: str, caption: str) -> bool:
    """Helper to send a PDF via the built-in bot logic."""
    try:
        # We need a bot instance. It needs an API instance (which we have).
        bot = IncodeBot(incode_instance)
        # Check if configured
        creds = load_credentials()
        if not creds.get("telegram_token") or not creds.get("allowed_user_id"):
            console.print("[yellow]Telegram Bot ist noch nicht konfiguriert.[/yellow]")
            console.print("Bitte starte einmal 'Telegram Bot starten' im Hauptmenü oder 'incode bot'.")
            return False
            
        chat_id = creds["allowed_user_id"]
        success = bot.send_document(chat_id, file_path, caption)
        return success
    except Exception as e:
        console.print(f"[error]Fehler beim Bot-Versand: {e}[/error]")
        return False

def render_next_duty_panel(duty: Any) -> None:
    if not duty: return

    # Format Date
    now = datetime.now()
    d_date = duty.begin.date()
    days_diff = (d_date - now.date()).days
    
    day_name = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][d_date.weekday()]
    date_str = f"{day_name}, {d_date.strftime('%d.%m.')}"
    
    relative_str = ""
    if days_diff == 0: relative_str = " (Heute)"
    elif days_diff == 1: relative_str = " (Morgen)"
    elif days_diff == 2: relative_str = " (Übermorgen)"
    elif days_diff < 7: relative_str = f" (in {days_diff} Tagen)"
    
    # Format Times
    time_str = f"{duty.begin.strftime('%H:%M')} - {duty.end.strftime('%H:%M')}"
    dur_str = f"({duty.duration_hours:g}h)"
    
    # Format Location / Vehicle
    loc = duty.location or "Unbekannt"
    veh = duty.vehicle or "Dienst"
    
    # Format Crew (Top 2 + count)
    crew_list = duty.crew
    crew_str = ", ".join(crew_list[:2])
    if len(crew_list) > 2: crew_str += f" +{len(crew_list)-2}"
    if not crew_str: crew_str = "-"
    
    # Build Grid
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="left")
    grid.add_column(justify="left")
    
    # Row 1: Date & Location
    grid.add_row(f"🚑  [bold white]{date_str}[/bold white][dim]{relative_str}[/dim]", f"📍  {loc}")
    # Row 2: Time & Crew
    grid.add_row(f"🕒  {time_str} [dim]{dur_str}[/dim]", f"👥  {crew_str}")
    # Row 3 (Optional): Vehicle if present
    if duty.vehicle:
        grid.add_row(f"🚗  {veh}", "")
        
    p = Panel(
        Align.center(grid),
        title="[bold green]Nächster Dienst[/bold green]",
        border_style="green",
        expand=False,
        padding=(1, 2)
    )
    console.print(Align.center(p))
    console.print() # Spacer

def interactive_menu(options: List[Tuple[str, Any]], title: str = "HAUPTMENÜ", dashboard_data: Any = None, current_user: Optional[str] = None, allow_escape: bool = True) -> Optional[Any]:
    """
    Renders an interactive menu navigated by arrow keys.
    options: list of tuples (Label, ReturnValue)
             e.g. [("Mein Dienstplan", "my_plan"), ("Beenden", "exit")]
    Returns: The ReturnValue of the selected option, or None if ESC is pressed.
    """
    selected_idx = 0
    
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        
        # Render Dashboard if present
        if dashboard_data:
            render_next_duty_panel(dashboard_data)
        
        if current_user:
            s_status = get_storage_status(current_user)
            s_short = "🔒 Keyring" if "Keyring" in s_status else "⚠️ JSON"
            s_color = "green" if "Keyring" in s_status else "yellow"
            console.print(Align.center(f"[dim]Angemeldet als: [bold white]{current_user}[/bold white] [{s_color}]({s_short})[/{s_color}][/dim]"))
            console.print() # Spacer
        
        console.print(Align.center(f"[header]{title}[/header]\n"))

        
        menu_grid = Table.grid(padding=(0, 0))
        menu_grid.add_column()
        
        for idx, (label, _) in enumerate(options):
            if idx == selected_idx:
                menu_grid.add_row(f"[bold green]> {label}[/bold green]")
            else:
                menu_grid.add_row(f"  {label}")
            # Add empty row for spacing
            menu_grid.add_row("")
        
        console.print(Align.center(menu_grid))
        
        hint = "⬆/⬇ Navigieren • ↵ Auswählen"
        if allow_escape:
            hint += " • ESC Zurück/Beenden"
        
        console.print(Align.center(f"\n[dim]{hint}[/dim]\n"))

        key = get_key()
        
        if key == KEY_UP or key == KEY_UP_ALT:
            selected_idx = (selected_idx - 1) % len(options)
        elif key == KEY_DOWN or key == KEY_DOWN_ALT:
            selected_idx = (selected_idx + 1) % len(options)
        elif key == KEY_ENTER:
            return options[selected_idx][1]
        elif key == KEY_ESC or (key and key.lower() == 'q'):
            if allow_escape:
                return None

def select_date_interactive() -> Optional[datetime]:
    """
    Interactive calendar date selection.
    """
    current_date = datetime.now()
    selected_date = current_date
    
    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print(Align.center(f"[header]DATUMS-AUSWAHL[/header]\n"))
        
        year, month = selected_date.year, selected_date.month
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]
        
        table = Table(title=f"{month_name} {year}", box=None, padding=(0, 1))
        for day_name in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
            table.add_column(day_name, justify="center", style="dim")
            
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append("")
                else:
                    d_str = str(day)
                    if day == selected_date.day:
                        row.append(f"[black on green]{d_str}[/]")
                    elif day == current_date.day and month == current_date.month and year == current_date.year:
                         row.append(f"[bold blue]{d_str}[/]")
                    else:
                        row.append(d_str)
            table.add_row(*row)
            
        console.print(Align.center(table))
        console.print(Align.center(f"\n[dim]Pfeiltasten zum Navigieren • ↵ Auswählen • ESC Abbrechen[/dim]"))
        
        key = get_key()
        
        if not key: continue

        if key == KEY_LEFT or key == KEY_LEFT_ALT:
            selected_date -= timedelta(days=1)
        elif key == KEY_RIGHT or key == KEY_RIGHT_ALT:
            selected_date += timedelta(days=1)
        elif key == KEY_UP or key == KEY_UP_ALT:
            selected_date -= timedelta(weeks=1)
        elif key == KEY_DOWN or key == KEY_DOWN_ALT:
            selected_date += timedelta(weeks=1)
        elif key == KEY_ENTER:
            return selected_date
        elif key == KEY_ESC or key.lower() == 'q':
            return None

class CenteredPrompt(Prompt):
    prompt_suffix = ""
    def make_prompt(self, default: Any) -> Text:
        return self.prompt
