# Incode CLI 🚑

**Version:** 1.7  
**Python:** 3.8+

Ein professionelles, terminal-basiertes Interface (TUI) für das **Incode / Maportal Dienstplan-System** des Roten Kreuzes.

Dieses Tool wurde entwickelt, um die oft langsame und unübersichtliche Web-Oberfläche durch eine schnelle, lokale und automatisierbare Lösung zu ersetzen. Es bietet erweiterte Funktionen wie algorithmische Urlaubsbrechnung, PDF-Exporte und einen integrierten Telegram-Bot.

---

## ✨ Features & Technische Highlights

### 📅 Intelligenter Dienstplan & Abwesenheits-Manager
Das Herzstück der Anwendung ist der neu entwickelte Abwesenheits-Parser (v1.7), der weit über die Standard-Anzeige hinausgeht:

*   **Hybrid-Datenquellen:** Kombiniert Daten aus fixierten Dienstplänen (`load.json`) mit genehmigten, aber noch nicht synchronisierten Anträgen (`loadWishes.json`).
*   **Gap Filling Algorithmus:** Erkennt Lücken zwischen genehmigten Urlauben und dem Dienstplan und füllt diese intelligent auf.
*   **Feiertags-Splitting:** Zerlegt Urlaubsblöcke automatisch, wenn sie gesetzliche österreichische Feiertage (inkl. variabler Osterfeiertage) enthalten, und markiert diese korrekt als "Sonderabwesenheit".
*   **Sunday Filler:** Erkennt fehlende "Abwesend"-Einträge an Sonntagen nach einer Urlaubswoche und generiert diese automatisch für eine lückenlose Ansicht.
*   **Netto-Urlaubsberechnung:** Berechnet den tatsächlichen Urlaubsverbrauch exklusive Wochenenden und Feiertagen.

### 🚑 Live-Operations
*   **Tagesplan:** Ruft den aktuellen Tagesstatus der Dienststelle ab, inkl. Fahrzeugbesatzungen und Zeiten.
*   **Live-Monitor:** Ein Auto-Refresh Modus für Infoscreens, der bei Änderungen (z.B. Mannschaftswechsel) sofort via Telegram benachrichtigen kann.

### 🛠️ Tooling & Export
*   **PDF Generation:** Erstellt saubere, druckfertige Dienstpläne mittels `reportlab`.
*   **iCal Sync:** Exportiert Dienste in das `.ics` Format zur Integration in Google Calendar / Outlook.
*   **Mitarbeiter-Datenbank:** Durchsucht das interne Verzeichnis nach Kontaktdaten, Dienstnummern und Qualifikationen.

### 🤖 Telegram Integration
Ein integrierter Bot-Modus (`src/bot.py`), der auf dem Server laufen kann und auf Befehle reagiert oder proaktiv Dienstplan-Updates pusht.

---

## 🚀 Installation

### Voraussetzungen
*   Python 3.8 oder höher
*   Zugriff auf das Incode-System (Login-Daten)

### Setup

1.  **Repository klonen**
    ```bash
    git clone https://github.com/manueloberberger/incode-cli.git
    cd incode-cli
    ```

2.  **Virtuelle Umgebung erstellen (Empfohlen)**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # oder: .venv\Scripts\activate  # Windows
    ```

3.  **Abhängigkeiten installieren**
    Das Projekt nutzt `rich` für das UI, `requests` für API-Calls und `reportlab` für PDFs.
    ```bash
    pip install -r requirements.txt
    ```

---

## 🎮 Benutzung

### Start
Starten Sie die interaktive Konsole:
```bash
python3 incode.py
```

Beim ersten Start werden Sie nach Ihren Zugangsdaten gefragt. Diese werden lokal in `.credentials.json` gespeichert. Das Skript setzt automatisch `chmod 600` auf diese Datei, um sie vor fremden Zugriffen zu schützen.

### Bot-Modus
Um den Telegram-Bot als Daemon laufen zu lassen:
```bash
python3 incode.py bot
```
*(Hinweis: Telegram-Token und User-ID müssen zuvor in der Config hinterlegt werden)*

---

## 🏗️ Projektstruktur

```
incode-cli/
├── incode.py           # Entrypoint & CLI-Routing
├── .credentials.json   # Lokale Konfiguration (ignoriert von git)
├── .incode_cache.json  # Temporärer API-Cache
└── src/
    ├── api.py          # Core-Logik: Session-Management, Retry-Logik, Parsing-Algorithmen
    ├── ui.py           # Darstellungsschicht: Rich Tables, Panels, Interaktive Menüs
    ├── config.py       # Globale Konstanten, Versionierung, Theme-Definitionen
    ├── ical.py         # iCalendar Generator
    ├── pdf.py          # PDF Report Engine
    ├── bot.py          # Telegram Bot Implementierung
    └── utils.py        # Hilfsfunktionen (Update-Check, Input-Handling)
```

### Caching-Strategie
Um die Serverlast zu minimieren und die Reaktionszeit zu verbessern, implementiert `src/api.py` einen dateibasierten Cache (`.incode_cache.json`) mit einer TTL (Time To Live) von 15 Minuten für schwere Abfragen wie den monatlichen Dienstplan. Live-Daten (Tagesplan) werden nicht gecached.

---

## ⚠️ Disclaimer

Dieses Projekt ist eine private Open-Source-Entwicklung und steht in keiner offiziellen Verbindung zum Roten Kreuz oder den Herstellern der Incode-Software. Die Nutzung erfolgt auf eigene Gefahr. Es werden keine Daten an Dritte übertragen – die Kommunikation findet ausschließlich direkt zwischen Ihrem Rechner und dem Incode-Server statt.