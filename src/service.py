import os
import sys
import platform
from pathlib import Path
from rich.align import Align
from src.config import console

def install_systemd_service() -> None:
    """Generate and optionally install systemd service for the Telegram bot."""
    
    # Check if running on Linux (systemd)
    if platform.system() != "Linux":
        console.print(Align.center("[yellow]Systemd services werden nur unter Linux unterstützt.[/yellow]"))
        console.print(Align.center("[dim]Für macOS nutze launchd (nicht implementiert).[/dim]"))
        return
    
    # Detect paths
    cwd = os.getcwd()
    script_path = os.path.join(cwd, "incode.py")
    venv_python = os.path.join(cwd, ".venv/bin/python")
    
    if not os.path.exists(venv_python):
        console.print(Align.center("[red]Fehler: .venv/bin/python nicht gefunden.[/red]"))
        console.print(Align.center("[yellow]Führe './install.sh' aus, um das Virtual Environment zu erstellen.[/yellow]"))
        return
    
    # Get current user
    current_user = os.environ.get("USER", "nobody")
    
    # Generate service file content
    service_content = f"""[Unit]
Description=Incode CLI Telegram Bot
After=network.target

[Service]
Type=simple
User={current_user}
WorkingDirectory={cwd}
ExecStart={venv_python} {script_path} bot
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
"""
    
    service_file_path = "/etc/systemd/system/incode-bot.service"
    
    console.print()
    console.print(Align.center("[bold cyan]Systemd Service Installer[/bold cyan]"))
    console.print()
    console.print(Align.center(f"[dim]Service wird installiert für Benutzer: {current_user}[/dim]"))
    console.print(Align.center(f"[dim]Arbeitsverzeichnis: {cwd}[/dim]"))
    console.print()
    
    # Check if running as root/sudo
    is_root = os.geteuid() == 0
    
    if is_root:
        # Attempt automatic installation
        try:
            # Write service file
            with open(service_file_path, 'w') as f:
                f.write(service_content)
            console.print(Align.center(f"[green]✓ Service-Datei erstellt: {service_file_path}[/green]"))
            
            # Reload systemd
            os.system("systemctl daemon-reload")
            console.print(Align.center("[green]✓ Systemd neu geladen[/green]"))
            
            # Enable service
            os.system("systemctl enable incode-bot.service")
            console.print(Align.center("[green]✓ Service aktiviert (Auto-Start)[/green]"))
            
            # Start service
            os.system("systemctl start incode-bot.service")
            console.print(Align.center("[green]✓ Service gestartet[/green]"))
            
            console.print()
            console.print(Align.center("[bold green]Installation erfolgreich![/bold green]"))
            console.print()
            console.print(Align.center("[dim]Nützliche Befehle:[/dim]"))
            console.print(Align.center("[info]systemctl status incode-bot[/info] - Status anzeigen"))
            console.print(Align.center("[info]journalctl -u incode-bot -f[/info] - Logs live anzeigen"))
            console.print(Align.center("[info]systemctl stop incode-bot[/info] - Service stoppen"))
            console.print(Align.center("[info]systemctl restart incode-bot[/info] - Service neustarten"))
            
        except Exception as e:
            console.print(Align.center(f"[red]Fehler bei der Installation: {e}[/red]"))
            sys.exit(1)
    else:
        # Print manual instructions
        console.print(Align.center("[yellow]Keine Root-Rechte erkannt. Manuelle Installation erforderlich.[/yellow]"))
        console.print()
        console.print(Align.center("[bold]Führe die folgenden Befehle aus:[/bold]"))
        console.print()
        
        # Save to temporary file for easy copy
        temp_file = "/tmp/incode-bot.service"
        with open(temp_file, 'w') as f:
            f.write(service_content)
        
        console.print(Align.center(f"[info]sudo cp {temp_file} {service_file_path}[/info]"))
        console.print(Align.center("[info]sudo systemctl daemon-reload[/info]"))
        console.print(Align.center("[info]sudo systemctl enable incode-bot.service[/info]"))
        console.print(Align.center("[info]sudo systemctl start incode-bot.service[/info]"))
        console.print()
        console.print(Align.center(f"[dim]Service-Datei vorbereitet: {temp_file}[/dim]"))
