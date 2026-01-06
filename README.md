# Incode CLI v1.0

Eine leistungsstarke CLI-Anwendung und ein Telegram-Bot zur Abfrage von Dienstplänen aus dem Rotes Kreuz Incode-System.

Dieses Tool ermöglicht es Sanitätern und Mitarbeitern, ihren persönlichen Dienstplan sowie den allgemeinen Tagesplan (Fahrzeuge, Besatzungen, Einsatzbereiche) effizient über das Terminal oder mobil via Telegram abzurufen. Es ersetzt die bisherigen Einzeltools `incode-checker` und `tg-incode-bot` durch eine zentrale, kombinierte Lösung.

## Features

- **Persönlicher Dienstplan:** Abfrage aller zukünftigen und vergangenen Dienste.
- **Tagesplan-Einsicht:** Komplette Übersicht aller Fahrzeuge und deren Besetzung für jeden beliebigen Tag.
- **Telegram-Bot:** Fordere deinen Plan von unterwegs an und erhalte ihn sofort als sauber formatiertes **PDF**.
- **Live-Monitor:** Ein interaktiver Modus im Terminal, der sich automatisch aktualisiert (ideal für Standorte oder Wachen).
- **Kollegen-Suche:** Finde schnell heraus, wann und wo bestimmte Kollegen eingeteilt sind.
- **iCal-Export:** (Optional) Synchronisiere deine Dienste mit deinem digitalen Kalender.

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
Startet das Terminal-Interface mit Menüführung:
```bash
./incode
# oder
python3 incode.py
```

### Telegram Bot Modus
Startet den Bot-Prozess:
```bash
./incode bot
# oder
python3 incode.py bot
```
Der Bot antwortet auf Befehle wie `/dienste` oder `/tagesplan` mit einer generierten PDF-Datei.

## Konfiguration
Die Zugangsdaten (Incode & Telegram) werden beim ersten Start sicher abgefragt und lokal in `.credentials.json` gespeichert. Die Datei wird automatisch mit restriktiven Leserechten (`600`) versehen.
