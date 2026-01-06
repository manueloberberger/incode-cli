# Incode CLI v1.0

Dies ist die kombinierte Version von `incode-checker` und `tg-incode-bot`.

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
Startet das klassische Terminal-Interface:
```bash
python main.py
```
Im Menü gibt es nun auch die Option "Telegram Bot starten".

### Bot Modus
Startet direkt den Telegram Bot:
```bash
python main.py bot
```
Beim ersten Start wirst du nach dem Bot-Token und deiner User ID gefragt, falls diese noch nicht konfiguriert sind.

## Konfiguration
Die Zugangsdaten (Incode & Telegram) werden in `.credentials.json` gespeichert.
