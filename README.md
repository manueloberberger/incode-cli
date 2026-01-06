# Incode CLI v1.0

Dies ist die kombinierte Version von `incode-checker` und `tg-incode-bot`.
Das Tool bietet ein interaktives Terminal-Interface sowie einen Telegram-Bot, der Dienstpläne direkt als PDF versendet.

## Installation

1. Erstelle ein Virtual Environment (optional, aber empfohlen):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Installiere die Abhängigkeiten:
   ```bash
   pip install -r requirements.txt
   ```

## Nutzung

### Interaktiver Modus (CLI)
Startet das klassische Terminal-Interface mit Menüführung:
```bash
./incode
# oder
python3 incode.py
```
Funktionen:
- Anzeige zukünftiger Dienste
- Tagesplan-Abfrage (Heute oder spezifisches Datum)
- Suche nach Kollegen
- **Live-Monitor** (Auto-Update)
- Telegram Bot starten

### Telegram Bot Modus
Startet den Bot, der auf Befehle reagiert:
```bash
./incode bot
# oder
python3 incode.py bot
```
Der Bot antwortet auf Befehle wie `/dienste` oder `/tagesplan` mit einer generierten **PDF-Datei** für eine bessere Übersicht.

## Konfiguration
Die Zugangsdaten (Incode & Telegram) werden beim ersten Start abgefragt und sicher in `.credentials.json` gespeichert.