# Incode CLI v1.1

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)
![Architecture](https://img.shields.io/badge/architecture-hybrid%20async-purple.svg)

Eine hochoptimierte CLI-Anwendung und ein reaktiver Telegram-Bot zur effizienten Interaktion mit dem **Incode-Dienstplansystem des Roten Kreuzes**.

In Version 1.1 wurde der Kern modernisiert: **Smart Caching** für sofortigen Start (auch offline), eine **asynchrone Bot-Engine** für schnellere Reaktionen und **standardkonforme Kalender-Exporte**.

## 🚀 Kernfunktionen

### 1. Interaktives Terminal-Interface (CLI)
Das CLI ist das Herzstück für die stationäre Nutzung (z.B. auf der Dienststelle oder am PC):
- **Smart Dashboard:** Zeigt sofort beim Start deine nächsten Dienste (lädt aus dem Cache, während im Hintergrund aktualisiert wird).
- **Tagesplan-Explorer:** Durchsuche den gesamten Dienstplan für heute oder ein beliebiges Datum.
- **Live-Monitor:** Ein spezialisierter Modus für Wachen-Monitore. Aktualisiert sich selbstständig und sendet bei Änderungen (z.B. Fahrzeugtausch) sofort eine PDF an Telegram.
- **Intelligente Suche:** Finde heraus, wann Kollegen Dienst haben.
- **Optimierte Exporte:** 
  - **PDF:** Generiert saubere Übersichten mit Zeitstempel im Dateinamen (z.B. `Tagesplan_2026-01-07_14-30.pdf`).
  - **iCal:** Vollständig standardkonforme `.ics` Dateien für Outlook, Google Kalender & Apple Calendar.

### 2. Modernisierter Telegram Bot v1.1
Der Bot wurde auf eine asynchrone Architektur umgestellt (`python-telegram-bot`), was ihn deutlich stabiler und reaktiver macht.
- **Befehle:**
  - `/start` - Übersicht und Hilfe.
  - `/dienste` - Sendet deinen persönlichen Dienstplan als PDF.
  - `/tagesplan` (oder `/heute`) - Sendet den aktuellen Tagesplan der Dienststelle als PDF.
- **Security:** Der Bot reagiert ausschließlich auf die konfigurierte `User-ID`. Fremde Anfragen werden ignoriert.

---

## 🛠 Installation & Setup

### Voraussetzungen
- **Python 3.8** oder neuer.
- Ein Computer mit **Linux**, **macOS** oder Windows.

### Installation

1. **Repository klonen:**
   ```bash
   git clone https://github.com/manueloberberger/incode-cli.git
   cd incode-cli
   ```

2. **Umgebung einrichten:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   chmod +x incode
   ```

3. **Starten:**
   ```bash
   ./incode
   ```
   *Beim ersten Start wirst du nach deinen Incode-Zugangsdaten gefragt. Diese werden lokal verschlüsselt in `.credentials.json` gespeichert.*

4. **Bot Einrichten (Optional):**
   Wähle im Menü "Telegram Bot" oder starte `./incode bot`. Du wirst nach deinem Bot-Token und deiner User-ID gefragt.

---

## 🧠 Technical Deep Dive (v1.1 Update)

### 1. Smart Caching Layer (`src/api.py`)
Um die Trägheit des Incode-Servers zu umgehen, implementiert v1.1 einen lokalen Cache (`.incode_cache.json`).
*   **Strategie:** Daten sind 15 Minuten lang gültig ("Fresh").
*   **Offline-First:** Ist der Server nicht erreichbar oder das Login fehlgeschlagen, werden automatisch die letzten bekannten Daten aus dem Cache geladen. Das ermöglicht den Zugriff auf den Dienstplan auch ohne Internetverbindung.

### 2. Async Bot Architecture (`src/bot.py`)
Die alte Polling-Loop wurde durch `python-telegram-bot` (asyncio) ersetzt.
*   **Non-Blocking:** Langsame PDF-Generierungen blockieren nicht mehr den Empfang neuer Nachrichten.
*   **Thread-Offloading:** Schwere Aufgaben (wie API-Requests oder PDF-Rendering) werden via `asyncio.to_thread` ausgelagert, um den Event-Loop flüssig zu halten.

### 3. API Reverse Engineering
Das Tool emuliert weiterhin einen Browser-Client, da keine öffentliche API existiert:
*   **Session-Hijacking:** Login via `login.php`, Extraktion der `PHPSESSID`.
*   **Token Extraction:** Automatisches Parsen von `x-incode-auth` Token und `orgUnitDataGuid` aus dem JavaScript-Quelltext der Antwortseite.

### 4. PDF & iCal Engine
*   **PDF:** Nutzung von `ReportLab` für extrem schnelle Generierung (< 0.1s) direkt im RAM. Dateinamen enthalten nun Zeitstempel zur Versionierung.
*   **iCal:** Umstellung auf die `icalendar` Library in v1.1 garantiert, dass Umlaute, Zeitzonen und Beschreibungen in allen Kalender-Apps korrekt dargestellt werden.

---

## 🏗 Projektstruktur

```
incode-cli/
├── incode.py           # Entry Point
├── .credentials.json   # Lokaler Config-Storage (Git-Ignored)
├── .incode_cache.json  # Temporärer Cache (Git-Ignored)
├── src/
│   ├── api.py          # Incode Session, Auth & Caching Logic
│   ├── bot.py          # Async Telegram Bot
│   ├── config.py       # Configuration & Constants
│   ├── ical.py         # iCal Generation (icalendar lib)
│   ├── pdf.py          # PDF Generation Engine
│   ├── ui.py           # TUI (Rich) & Interactive Menus
│   └── utils.py        # Helpers
└── requirements.txt    # Python Dependencies
```

---
*Hinweis: Dieses Tool steht in keiner offiziellen Verbindung zum Roten Kreuz. Es ist ein Community-Projekt zur Verbesserung der Usability.*