from datetime import datetime
from typing import Any

from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.pretty import Pretty

from src.config import console, BANNER
from src.utils import clear_screen, centered_input, wait_for_return, get_key, KEY_ESC, KEY_ENTER
from src.ui.components import interactive_menu
from src.ui.dashboard import show_future_duties

def show_staff_search(incode: Any) -> None:
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold header]MITARBEITER-VERZEICHNIS[/bold header]"))
    console.print()
    console.print(Align.center("[dim]Suche nach Name, PNR oder Kürzel ist möglich ...[/dim]"))
    console.print()
    
    query = centered_input("[bold green]>[/bold green] ")
    if not query:
        return # ESC pressed
    
    console.print()
    with Live(Align.center(Spinner("dots", text=f" Suche nach '{query}' ...")), console=console, transient=True):
        results = incode.search_staff_contact(query)
        
    if not results:
        console.print(Align.center(f"\n[warning]Nichts gefunden für '{query}'.[/warning]"))
        wait_for_return()
        return

    # If multiple results, let user choose interactively
    selected_person = results[0]
    if len(results) > 1:
        options = []
        for r in results:
            label = f"{r.get('_display_name')} [dim]({r.get('personalnummer', 'n.a.')})[/dim]"
            options.append((label, r))
        
        selected_person = interactive_menu(options, title=f"TREFFER-AUSWAHL ({len(results)})")
        if not selected_person: return

    _display_staff_details_loop(selected_person)

def _display_staff_details_loop(p: Any) -> None:
    show_details = False
    
    # Helper for nice dates
    def fmt_date(s):
        if not s or len(str(s)) < 10: return "-"
        try:
            return datetime.strptime(str(s)[:10], '%Y-%m-%d').strftime('%d.%m.%Y')
        except: return s

    # Helper for phone numbers
    def fmt_phone(s):
        if not s: return ""
        s = str(s).strip()
        if s.startswith("00"): s = "+" + s[2:]
        if s.startswith("+43") and len(s) > 4:
            # Simple formatting: +43 664 1234567
            return f"{s[:3]} {s[3:6]} {s[6:]}"
        return s

    while True:
        clear_screen()
        console.print(Align.center(BANNER))
        console.print(f"\n[bold header]   {p.get('_display_name')}   [/bold header]\n", justify="center")
        
        # Try to extract Service Number (Dienstnummer) from Occupations
        service_number = "-"
        occs = p.get('ressourceToOccupations', [])
        for o in occs:
            name = str(o.get('name', ''))
            parts = name.split('.')
            if parts and parts[0].isdigit():
                service_number = parts[0]
                break
            if name.split(' ')[0].isdigit():
                 service_number = name.split(' ')[0]

        # --- BASIC INFO ---
        grid_basic = Table.grid(expand=False, padding=(0, 2))
        grid_basic.add_column(style="bold cyan", justify="right")
        grid_basic.add_column(style="white")
        
        # Address Construction
        addr_parts = []
        if p.get('street'): addr_parts.append(p.get('street'))
        if p.get('zip') or p.get('city'): 
            city_line = f"{p.get('zip', '')} {p.get('city', '')}".strip()
            if city_line: addr_parts.append(city_line)
        address_str = ", ".join(addr_parts) if addr_parts else None

        # Helper for Role
        def fmt_role(person):
            role = person.get('maportal_role', '')
            if role == 'dutytype_active': return "Aktiv"
            return role

        basic_fields = [
            ("Dienstnummer", lambda _: service_number),
            ("Incode-ID (PNR)", 'personalnummer'),
            ("Rolle (Maportal)", fmt_role),
            ("Telefon (Dienst)", lambda x: fmt_phone(x.get('telefon'))),
            ("Telefon (Privat)", lambda x: fmt_phone(x.get('telefon_privat'))),
            ("Mobil", lambda x: fmt_phone(x.get('handy') or x.get('mobile'))),
            ("Email", 'email'),
            ("Email (Privat)", 'email_privat'),
            ("Adresse", lambda _: address_str)
        ]
        
        for label, key in basic_fields:
            if callable(key): val = key(p)
            else: val = str(p.get(key, ''))
            if val and val != "None" and val != "-":
                grid_basic.add_row(label + ":", str(val))
        
        console.print(Align.center(Panel(Align.center(grid_basic), title="[bold]Kontakt & Basisdaten[/bold]", border_style="blue", padding=(1, 2), expand=False)))

        # --- BALANCES (Stats) ---
        saldo_u = p.get('saldo_urlaub')
        saldo_za = p.get('saldo_za')
        
        if saldo_u or saldo_za:
            stats_grid = Table.grid(expand=True, padding=(0, 4))
            stats_grid.add_column(justify="center", ratio=1)
            stats_grid.add_column(justify="center", ratio=1)
            
            try:
                u_color = "green" if float(str(saldo_u or 0).replace(',', '.')) > 0 else "red"
                za_color = "green" if float(str(saldo_za or 0).replace(',', '.')) > 0 else "red"
            except:
                u_color = "white"
                za_color = "white"
            
            stats_grid.add_row(
                f"[bold]Urlaub:[/bold] [{u_color}]{saldo_u or '0'}h[/{u_color}]",
                f"[bold]Zeitausgleich:[/bold] [{za_color}]{saldo_za or '0'}h[/{za_color}]"
            )
            console.print(Align.center(Panel(stats_grid, title="Salden (Live)", border_style="yellow", expand=False)))

        # --- DETAILS ---
        if show_details:
            # Extended Attributes
            grid_ext = Table.grid(expand=False, padding=(0, 2))
            grid_ext.add_column(style="dim cyan", justify="right")
            grid_ext.add_column(style="dim white")

            ext_fields = [
                ("Benutzername", 'maportal_manualName'),
                ("Geburtsdatum", lambda x: fmt_date(x.get('birthdate'))),
                ("Letzter Login", lambda x: fmt_date(x.get('maportal_lastLogin'))),
                ("Gültig ab", lambda x: fmt_date(x.get('validFrom'))),
                ("Gültig bis", lambda x: fmt_date(x.get('validTo'))),
                ("Erstellt", 'created'),
                ("Bearbeitet", 'updated'),
                ("Ursprung", 'origin'),
                ("Info", 'info')
            ]
            
            has_ext = False
            for label, key in ext_fields:
                if callable(key): val = key(p)
                else: val = str(p.get(key, ''))
                if val and val != "None" and val != "-":
                    grid_ext.add_row(label + ":", str(val))
                    has_ext = True
            
            if has_ext:
                console.print(Align.center(Panel(Align.center(grid_ext), title="System-Daten", border_style="dim", expand=False)))

            # Roles Table
            if occs:
                t_occ = Table(title="Rollen / Beschäftigung", box=None, show_edge=False, padding=(0,1), expand=True, header_style="bold white on black")
                t_occ.add_column("Bezeichnung", style="bold white")
                t_occ.add_column("Zeitraum", style="dim")
                t_occ.add_column("Ext. ID", style="dim")
                for o in occs:
                    period = f"{fmt_date(o.get('begin'))} - {fmt_date(o.get('end'))}"
                    t_occ.add_row(o.get('name', '-'), period, o.get('externalId', ''))
                console.print(Align.center(t_occ))
                console.print("")

            # Skills
            skills = p.get('staffToSkills', [])
            if skills:
                t_skill = Table(title=f"Qualifikationen ({len(skills)})", box=None, show_edge=False, padding=(0,1), expand=True, header_style="bold white on black")
                t_skill.add_column("Skill", style="cyan") 
                t_skill.add_column("Zeitraum", style="dim")
                for s in skills:
                    name = s.get('name') or s.get('text') or s.get('externalId', '-')
                    period = f"{fmt_date(s.get('begin'))} - {fmt_date(s.get('end'))}"
                    t_skill.add_row(name, period)
                console.print(Align.center(t_skill))
                console.print("")

            # Groups
            groups = p.get('ressourceToGroups', [])
            if groups:
                t_grp = Table(title=f"Gruppen-Zugehörigkeit ({len(groups)})", box=None, show_edge=False, padding=(0,1), expand=True, header_style="bold white on black")
                t_grp.add_column("Gruppen", style="dim")
                t_grp.add_column("Zeitraum", style="dim")
                for g in groups:
                    name = g.get('name') or g.get('text') or (g.get('groupDataGuid', '')[:30] + "...")
                    period = f"{fmt_date(g.get('begin'))} - {fmt_date(g.get('end'))}"
                    t_grp.add_row(name, period)
                console.print(Align.center(t_grp))

        # Footer
        toggle_txt = "weniger Details" if show_details else "mehr Details"
        console.print(Align.center(f"\n[dim]Drücke 'd' für {toggle_txt}, 'r' für RAW Dump, oder ENTER zum Beenden ...[/dim]"))
        
        k = get_key()
        if k and k.lower() == 'd':
            show_details = not show_details
        elif k and k.lower() == 'r':
            console.print(Pretty(p))
            wait_for_return()
        elif k == KEY_ENTER or (k and k.lower() == 'q') or k == KEY_ESC:
            return

def show_colleague_search(incode) -> None:
    """Shows a dedicated page for searching colleague duties."""
    clear_screen()
    console.print(Align.center(BANNER))
    console.print()
    console.print(Align.center("[bold header]GEMEINSAME DIENSTE[/bold header]"))
    console.print()
    console.print(Align.center("[dim]Name des Kollegen eingeben ...[/dim]"))
    console.print()

    name = centered_input("[bold green]>[/bold green] ")
    if not name:
        return
        
    console.print() # Spacer
    show_future_duties(incode, search_colleague=name)
