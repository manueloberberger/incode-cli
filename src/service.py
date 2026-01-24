import os
import sys
import platform
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from rich.align import Align
from src.config import console, load_credentials
from src.ui import interactive_menu

def select_user_for_service(specific_user: Optional[str] = None) -> Dict[str, Any]:
    """Select which user account to run the service as."""
    creds = load_credentials()
    users = creds.get('users', [])
    
    if not users:
        console.print(Align.center("[red]Keine Benutzer konfiguriert.[/red]"))
        console.print(Align.center("[yellow]Bitte führe './incode' aus und füge einen Benutzer hinzu.[/yellow]"))
        sys.exit(1)
    
    # If specific user requested
    if specific_user:
        target_user = next((u for u in users if u['username'].lower() == specific_user.lower() or (u.get('real_name') and specific_user.lower() in u['real_name'].lower())), None)
        if not target_user:
            console.print(Align.center(f"[red]Benutzer '{specific_user}' nicht gefunden.[/red]"))
            sys.exit(1)
        return target_user  # type: ignore[no-any-return]
    
    # If only one user, auto-select
    if len(users) == 1:
        return users[0]  # type: ignore[no-any-return]
    
    # Multiple users - show menu
    console.print()
    console.print(Align.center("[bold cyan]Für welchen Benutzer soll der Service installiert werden?[/bold cyan]"))
    console.print()
    
    options: List[Tuple[str, Any]] = []
    for user in users:
        display_str = f"👤  {user['username']}"
        if user.get('real_name'):
            display_str += f" ({user['real_name']})"
        options.append((display_str, user))
    
    selected = interactive_menu(options, title="BENUTZER AUSWAHL")
    if not selected:
        console.print(Align.center("[yellow]Abgebrochen.[/yellow]"))
        sys.exit(0)
    
    return selected  # type: ignore[no-any-return]

def install_systemd_service(bot_user: Dict[str, Any]) -> None:
    """Install systemd service for Linux."""
    cwd = os.getcwd()
    script_path = os.path.join(cwd, "incode.py")
    venv_python = os.path.join(cwd, ".venv/bin/python")
    
    if not os.path.exists(venv_python):
        console.print(Align.center("[red]Fehler: .venv/bin/python nicht gefunden.[/red]"))
        console.print(Align.center("[yellow]Führe './install.sh' aus, um das Virtual Environment zu erstellen.[/yellow]"))
        return
    
    current_user = os.environ.get("USER", "nobody")
    bot_username = bot_user['username']
    safe_name = bot_username.replace(" ", "_").lower()
    
    service_content = f"""[Unit]
Description=Incode CLI Telegram Bot ({bot_username})
After=network.target

[Service]
Type=simple
User={current_user}
WorkingDirectory={cwd}
ExecStart={venv_python} {script_path} bot --user {bot_username}
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
"""
    
    service_file_path = f"/etc/systemd/system/incode-bot-{safe_name}.service"
    
    console.print()
    console.print(Align.center("[bold cyan]Linux Systemd Service Installer[/bold cyan]"))
    console.print()
    console.print(Align.center(f"[dim]Bot-Benutzer: {bot_username}[/dim]"))
    console.print(Align.center(f"[dim]System-Benutzer: {current_user}[/dim]"))
    console.print(Align.center(f"[dim]Arbeitsverzeichnis: {cwd}[/dim]"))
    console.print()
    
    is_root = os.geteuid() == 0
    
    if is_root:
        try:
            with open(service_file_path, 'w') as f:
                f.write(service_content)
            console.print(Align.center(f"[green]✓ Service-Datei erstellt: {service_file_path}[/green]"))
            
            os.system("systemctl daemon-reload")
            console.print(Align.center("[green]✓ Systemd neu geladen[/green]"))
            
            os.system(f"systemctl enable incode-bot-{safe_name}.service")
            console.print(Align.center("[green]✓ Service aktiviert (Auto-Start)[/green]"))
            
            os.system(f"systemctl start incode-bot-{safe_name}.service")
            console.print(Align.center("[green]✓ Service gestartet[/green]"))
            
            console.print()
            console.print(Align.center("[bold green]Installation erfolgreich![/bold green]"))
            console.print()
            console.print(Align.center("[dim]Nützliche Befehle:[/dim]"))
            console.print(Align.center(f"[info]systemctl status incode-bot-{safe_name}[/info] - Status anzeigen"))
            console.print(Align.center(f"[info]journalctl -u incode-bot-{safe_name} -f[/info] - Logs live anzeigen"))
            console.print(Align.center(f"[info]systemctl stop incode-bot-{safe_name}[/info] - Service stoppen"))
            console.print(Align.center(f"[info]systemctl restart incode-bot-{safe_name}[/info] - Service neustarten"))
            
        except Exception as e:
            console.print(Align.center(f"[red]Fehler bei der Installation: {e}[/red]"))
            sys.exit(1)
    else:
        temp_file = f"/tmp/incode-bot-{safe_name}.service"
        script_file = f"/tmp/install-incode-bot-{safe_name}.sh"
        
        with open(temp_file, 'w') as f:
            f.write(service_content)
        
        # Create installation script
        install_script = f"""#!/bin/bash
set -e

echo "🚀 Installiere Incode Bot Service für {bot_username}..."
echo ""

cp {temp_file} {service_file_path}
echo "✓ Service-Datei kopiert"

systemctl daemon-reload
echo "✓ Systemd neu geladen"

systemctl enable incode-bot-{safe_name}.service
echo "✓ Service aktiviert (Auto-Start)"

systemctl start incode-bot-{safe_name}.service
echo "✓ Service gestartet"

echo ""
echo "✅ Installation erfolgreich!"
echo ""
echo "Nützliche Befehle:"
echo "  systemctl status incode-bot-{safe_name}"
echo "  journalctl -u incode-bot-{safe_name} -f"
"""
        
        with open(script_file, 'w') as f:
            f.write(install_script)
        os.chmod(script_file, 0o755)
        
        console.print(Align.center("[yellow]Keine Root-Rechte erkannt.[/yellow]"))
        console.print()
        console.print(Align.center("[bold]Führe diesen Befehl aus:[/bold]"))
        console.print()
        console.print(Align.center(f"[info]sudo bash {script_file}[/info]"))
        console.print()
        console.print(Align.center(f"[dim]Installation wird automatisch durchgeführt.[/dim]"))

def install_launchd_service(bot_user: Dict[str, Any]) -> None:
    """Install launchd service for macOS."""
    cwd = os.getcwd()
    script_path = os.path.join(cwd, "incode.py")
    venv_python = os.path.join(cwd, ".venv/bin/python")
    
    if not os.path.exists(venv_python):
        console.print(Align.center("[red]Fehler: .venv/bin/python nicht gefunden.[/red]"))
        console.print(Align.center("[yellow]Führe './install.sh' aus, um das Virtual Environment zu erstellen.[/yellow]"))
        return
    
    bot_username = bot_user['username']
    safe_name = bot_username.replace(" ", "_").lower()
    
    # Create logs directory
    logs_dir = os.path.join(cwd, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.incode.bot.{safe_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{venv_python}</string>
        <string>{script_path}</string>
        <string>bot</string>
        <string>--user</string>
        <string>{bot_username}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{cwd}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{logs_dir}/bot-{safe_name}.log</string>
    <key>StandardErrorPath</key>
    <string>{logs_dir}/bot-{safe_name}.err</string>
</dict>
</plist>
"""
    
    home = os.path.expanduser("~")
    launchagents_dir = os.path.join(home, "Library", "LaunchAgents")
    os.makedirs(launchagents_dir, exist_ok=True)
    
    plist_path = os.path.join(launchagents_dir, f"com.incode.bot.{safe_name}.plist")
    
    console.print()
    console.print(Align.center("[bold cyan]macOS Launchd Service Installer[/bold cyan]"))
    console.print()
    console.print(Align.center(f"[dim]Bot-Benutzer: {bot_username}[/dim]"))
    console.print(Align.center(f"[dim]Arbeitsverzeichnis: {cwd}[/dim]"))
    console.print()
    
    try:
        with open(plist_path, 'w') as f:
            f.write(plist_content)
        console.print(Align.center(f"[green]✓ Plist-Datei erstellt: {plist_path}[/green]"))
        
        # Load the service
        os.system(f"launchctl load {plist_path}")
        console.print(Align.center("[green]✓ Service geladen und gestartet[/green]"))
        
        console.print()
        console.print(Align.center("[bold green]Installation erfolgreich![/bold green]"))
        console.print()
        console.print(Align.center("[dim]Nützliche Befehle:[/dim]"))
        console.print(Align.center(f"[info]launchctl list | grep incode[/info] - Status anzeigen"))
        console.print(Align.center(f"[info]tail -f {logs_dir}/bot-{safe_name}.log[/info] - Logs live anzeigen"))
        console.print(Align.center(f"[info]launchctl unload {plist_path}[/info] - Service stoppen"))
        console.print(Align.center(f"[info]launchctl load {plist_path}[/info] - Service starten"))
        
    except Exception as e:
        console.print(Align.center(f"[red]Fehler bei der Installation: {e}[/red]"))
        sys.exit(1)

def install_service(specific_user: Optional[str] = None) -> None:
    """Main entry point for service installation."""
    os_type = platform.system()
    
    if os_type not in ["Linux", "Darwin"]:
        console.print(Align.center(f"[red]OS '{os_type}' wird nicht unterstützt.[/red]"))
        console.print(Align.center("[yellow]Nur Linux (systemd) und macOS (launchd) werden unterstützt.[/yellow]"))
        return
    
    # Select user
    bot_user = select_user_for_service(specific_user)
    
    # Route to appropriate installer
    if os_type == "Linux":
        install_systemd_service(bot_user)
    elif os_type == "Darwin":
        install_launchd_service(bot_user)

def uninstall_service(specific_user: Optional[str] = None) -> None:
    """Uninstall the service."""
    os_type = platform.system()
    
    if os_type not in ["Linux", "Darwin"]:
        console.print(Align.center(f"[red]OS '{os_type}' wird nicht unterstützt.[/red]"))
        return
    
    # Get list of installed services
    installed_services = get_installed_services()
    
    if not installed_services:
        console.print()
        console.print(Align.center("[yellow]Keine Services installiert.[/yellow]"))
        return
    
    # If only one service installed, auto-select it
    if len(installed_services) == 1 and not specific_user:
        bot_username = installed_services[0]
        console.print()
        console.print(Align.center(f"[dim]Deinstalliere Service für {bot_username}...[/dim]"))
    else:
        # Multiple services or specific user requested
        bot_user = select_user_for_service(specific_user)
        bot_username = bot_user['username']
    
    safe_name = bot_username.replace(" ", "_").lower()
    
    console.print()
    console.print(Align.center("[bold cyan]Service Deinstallation[/bold cyan]"))
    console.print()
    
    if os_type == "Linux":
        service_name = f"incode-bot-{safe_name}.service"
        service_file = f"/etc/systemd/system/{service_name}"
        
        is_root = os.geteuid() == 0
        if is_root:
            try:
                os.system(f"systemctl stop {service_name}")
                os.system(f"systemctl disable {service_name}")
                if os.path.exists(service_file):
                    os.remove(service_file)
                os.system("systemctl daemon-reload")
                console.print(Align.center("[green]✓ Service erfolgreich deinstalliert![/green]"))
            except Exception as e:
                console.print(Align.center(f"[red]Fehler: {e}[/red]"))
        else:
            console.print(Align.center("[yellow]Root-Rechte erforderlich. Führe aus:[/yellow]"))
            console.print(Align.center(f"[info]sudo systemctl stop {service_name}[/info]"))
            console.print(Align.center(f"[info]sudo systemctl disable {service_name}[/info]"))
            console.print(Align.center(f"[info]sudo rm {service_file}[/info]"))
            console.print(Align.center("[info]sudo systemctl daemon-reload[/info]"))
    
    elif os_type == "Darwin":
        home = os.path.expanduser("~")
        plist_path = os.path.join(home, "Library", "LaunchAgents", f"com.incode.bot.{safe_name}.plist")
        
        try:
            if os.path.exists(plist_path):
                os.system(f"launchctl unload {plist_path}")
                os.remove(plist_path)
                console.print(Align.center("[green]✓ Service erfolgreich deinstalliert![/green]"))
            else:
                console.print(Align.center("[yellow]Service nicht gefunden.[/yellow]"))
        except Exception as e:
            console.print(Align.center(f"[red]Fehler: {e}[/red]"))

def check_service_status() -> None:
    """Check status of installed services."""
    import subprocess
    os_type = platform.system()
    
    console.print()
    console.print(Align.center("[bold cyan]Service Status[/bold cyan]"))
    console.print()
    
    if os_type == "Linux":
        console.print(Align.center("[dim]Installierte Incode Bot Services:[/dim]"))
        console.print()
        
        result = subprocess.run(
            ["systemctl", "list-units", "incode-bot-*", "--all", "--no-legend"],
            capture_output=True, text=True
        )
        
        if result.stdout.strip():
            # Show service lines
            for line in result.stdout.split('\n'):
                if line.strip() and 'incode-bot-' in line:
                    console.print(Align.center(f"[green]{line}[/green]"))
            console.print()
            console.print(Align.center("[dim]Tipp: 'journalctl -u incode-bot-<name> -f' für Live-Logs[/dim]"))
        else:
            console.print(Align.center("[yellow]💤 Keine Services installiert[/yellow]"))
            console.print()
            console.print(Align.center("[dim]Nutze '🟢 Als Systemdienst installieren' um den Bot zu installieren.[/dim]"))
            
    elif os_type == "Darwin":
        console.print(Align.center("[dim]Installierte Incode Bot Services:[/dim]"))
        console.print()
        
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True
        )
        
        found = False
        for line in result.stdout.split('\n'):
            if 'incode' in line.lower():
                console.print(Align.center(f"[green]{line}[/green]"))
                found = True
        
        if found:
            console.print()
            console.print(Align.center("[dim]Tipp: 'tail -f logs/bot-<name>.log' für Live-Logs[/dim]"))
        else:
            console.print(Align.center("[yellow]💤 Keine Services installiert[/yellow]"))
            console.print()
            console.print(Align.center("[dim]Nutze '🟢 Als Systemdienst installieren' um den Bot zu installieren.[/dim]"))
    else:
        console.print(Align.center(f"[yellow]OS '{os_type}' wird nicht unterstützt.[/yellow]"))

def has_installed_services() -> bool:
    """Check if any services are installed."""
    return len(get_installed_services()) > 0

def get_installed_services() -> List[str]:
    """Get list of usernames with installed services."""
    os_type = platform.system()
    services = []
    
    if os_type == "Linux":
        import subprocess
        result = subprocess.run(
            ["systemctl", "list-units", "incode-bot-*", "--all", "--no-pager", "--no-legend"],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if line and 'incode-bot-' in line:
                # Extract username from service name
                parts = line.split()
                if parts:
                    service_name = parts[0]
                    # incode-bot-7003127.service -> 7003127
                    username = service_name.replace('incode-bot-', '').replace('.service', '')
                    services.append(username)
    elif os_type == "Darwin":
        home = os.path.expanduser("~")
        launchagents_dir = os.path.join(home, "Library", "LaunchAgents")
        if os.path.exists(launchagents_dir):
            import glob
            plists = glob.glob(os.path.join(launchagents_dir, "com.incode.bot.*.plist"))
            for plist in plists:
                # com.incode.bot.7003127.plist -> 7003127
                basename = os.path.basename(plist)
                username = basename.replace('com.incode.bot.', '').replace('.plist', '')
                services.append(username)
    
    return services
