"""Personal roster, filtered exports and clearly separated statistics."""
from collections import Counter
from datetime import datetime
from typing import Any, List, Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table

from src.config import BANNER, console
from src.ical import export_to_ics
from src.models import Duty
from src.pdf import export_to_pdf
from src.ui.components import interactive_menu, send_pdf_via_bot
from src.ui.network import network_view
from src.utils import (clear_screen, duty_hours, filter_duties, flush_input,
                       get_key, duty_category, wait_for_return)


def _count_table(title: str, label: str, counts: Counter[str]) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAD, header_style="stats")
    table.add_column(label)
    table.add_column("Anzahl", justify="right")
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        table.add_row(name, f"{count}×")
    return table


def _render_statistics(duties: List[Duty], now: datetime) -> None:
    hours = Table(title="Stunden der angezeigten Dienste", box=box.SIMPLE_HEAD,
                  header_style="stats")
    for heading in ("Monat", "Geleistet", "Geplant / laufend", "Gesamt"):
        hours.add_column(heading, justify="left" if heading == "Monat" else "right")
    completed_total = planned_total = 0.0
    for month, (completed, planned) in sorted(duty_hours(duties, now).items()):
        hours.add_row(month, f"{completed:g}", f"{planned:g}", f"{completed + planned:g}")
        completed_total += completed
        planned_total += planned
    hours.add_section()
    hours.add_row("GESAMT (Std.)", f"{completed_total:g}", f"{planned_total:g}",
                  f"{completed_total + planned_total:g}")
    console.print(Align.center(hours))
    console.print(Align.center(Columns([
        _count_table("Dienst-Statistik", "Dienst", Counter(duty_category(d) for d in duties)),
        _count_table("Dienststellen", "Dienststelle", Counter(d.location or "Ohne Dienststelle" for d in duties)),
    ], align="center")))
    console.print(Align.center("[dim]Auswertung der geladenen Dienste. Stunden zählen zum Startmonat; laufende Dienste unter geplant.[/dim]"))


@network_view
def show_future_duties(incode: Any, search_colleague: Optional[str] = None) -> None:
    period = "all"
    label = "Alle geladenen Dienste"
    refresh = False
    with Live(Align.center(Spinner("dots", text="Lade Dienstplan …")), console=console, transient=True):
        loaded = incode.load_future_duties(override_name=search_colleague)
    while True:
        if refresh:
            loaded = incode.load_future_duties(use_cache=False, override_name=search_colleague)
            refresh = False
        now = datetime.now()
        duties = filter_duties(loaded, period, now)
        if search_colleague:
            duties = [d for d in duties if any(search_colleague.casefold() in name.casefold() for name in d.crew)]
        clear_screen()
        console.print(Align.center(BANNER))
        title = "MEIN DIENSTPLAN" if not search_colleague else f"GEMEINSAME DIENSTE MIT {search_colleague}"
        console.print(Align.center(title))
        console.print(Align.center(label))
        status = getattr(incode, "data_status", "")
        if isinstance(status, str) and status:
            console.print(Align.center(f"[dim]{status}[/dim]"))
        table = Table(box=box.SIMPLE_HEAD, header_style="header")
        for heading in ("Datum", "Zeit", "Ort", "Fzg", "Besatzung / Dienstart"):
            table.add_column(heading)
        for duty in duties:
            end = duty.end.strftime("%H:%M")
            if duty.end.date() != duty.begin.date():
                end += f" ({duty.end:%d.%m.})"
            table.add_row(duty.begin.strftime("%d.%m.%Y"),
                          f"{duty.begin:%H:%M}–{end} ({duty.duration_hours:g}h)",
                          duty.location or "–", duty.vehicle or "–",
                          ", ".join(duty.crew) or duty.duty_type or "–")
        if duties:
            console.print(Align.center(table))
            if not search_colleague:
                _render_statistics(duties, now)
        else:
            console.print(Align.center("[info]Keine Dienste für diesen Filter gefunden.[/info]"))
        console.print(Align.center("[dim]F: Zeitraum · R: neu laden · P: PDF · C: Kalender · T: PDF & Telegram · Andere Taste: zurück[/dim]"))
        flush_input()
        key = (get_key() or "").lower()
        if key == "r":
            refresh = True
            continue
        if key == "f":
            options = [("Alle geladenen Dienste", "all"), ("Bereits geleistet", "completed"),
                       ("Geplant / laufend", "planned"), ("Aktueller Monat", "month"),
                       ("Aktuelles Jahr", "year")]
            options.extend((month, f"month:{month}") for month in
                           sorted({d.begin.strftime("%Y-%m") for d in loaded}))
            selected = interactive_menu(options, title="ZEITRAUM WÄHLEN")
            if selected:
                period = selected
                label = next(text for text, value in options if value == selected)
            continue
        if key not in ("p", "c", "t"):
            return
        if not duties:
            continue
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Dienstplan_{timestamp}"
        if key == "c":
            export_to_ics(duties, filename + ".ics")
        elif export_to_pdf(duties, filename + ".pdf") and key == "t":
            if send_pdf_via_bot(incode, filename + ".pdf", f"Dienstplan – {label}"):
                console.print("[success]PDF erfolgreich per Telegram gesendet.[/success]")
        wait_for_return()
