"""Shared recoverable network errors for terminal views."""
from functools import wraps
from typing import Any, Callable
from rich.align import Align
from src.config import console
from src.exceptions import ApiError
from src.utils import get_key


def network_view(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        while True:
            try:
                return view(*args, **kwargs)
            except ApiError:
                console.print(Align.center(
                    "[error]Daten konnten nicht vollständig geladen werden. "
                    "Bitte Verbindung und Anmeldung prüfen.[/error]"))
                console.print(Align.center("[dim]R: erneut laden · Andere Taste: zurück[/dim]"))
                if (get_key() or "").lower() != "r":
                    return None
    return wrapped
