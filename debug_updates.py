import sys
import os
sys.path.append(os.getcwd())
from src.utils import check_for_updates
from src.config import console

console.print("[bold]Running Check for Updates Isolation Test[/bold]")
try:
    console.print("Calling check_for_updates(debug=True)...")
    res = check_for_updates(debug=True)
    console.print(f"Result: {res}")
except Exception as e:
    console.print(f"[red]Exception:[/red] {e}")
