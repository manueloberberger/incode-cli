"""
User Interface module for incode-cli.

This package contains all TUI (Terminal User Interface) components built with Rich.
Each submodule handles a specific view or set of UI components.

Submodules:
    components: Shared UI widgets (menus, date pickers, prompts)
    dashboard: Future duties view with statistics
    daily_plan: Single day duty plan view
    absences: Vacation and absence management view
    staff: Staff directory and colleague search
    events: Event duties view
    live: Live monitoring mode
    settings: User settings menu
"""
from .components import interactive_menu, select_date_interactive, CenteredPrompt, render_next_duty_panel
from .dashboard import show_future_duties
from .daily_plan import show_daily_plan
from .absences import show_absences
from .staff import show_staff_search, show_colleague_search
from .live import show_live_monitor
from .events import show_events_menu
from .settings import show_settings_menu

__all__ = [
    "interactive_menu",
    "select_date_interactive",
    "CenteredPrompt",
    "render_next_duty_panel",
    "show_future_duties",
    "show_daily_plan",
    "show_absences",
    "show_staff_search",
    "show_colleague_search",
    "show_live_monitor",
    "show_events_menu",
    "show_settings_menu",
]
