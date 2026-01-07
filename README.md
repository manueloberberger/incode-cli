# Incode CLI - Advanced Staff Portal Integration

Incode CLI ist ein leistungsfähiges Python-basiertes Kommandozeilen-Tool (CLI) zur Automatisierung und Visualisierung von Daten aus dem Rotes Kreuz Dienstplan-Portal (Incode StaffPortal). Es wurde entwickelt, um Einsatzkräften einen schnellen, gefilterten und funktional erweiterten Zugriff auf ihre Dienstpläne, Abwesenheiten und Veranstaltungen zu ermöglichen.

## 🚀 Kernfunktionen

- **📅 Mein Dienstplan:** Tabellarische Übersicht zukünftiger Dienste inklusive Stunden-Statistiken pro Monat und Dienststellen-Auswertungen. Export als PDF, iCal oder direkt per Telegram.
- **🌴 Abwesenheiten:** Übersicht über Urlaub, Krankenstände und ZA-Wünsche. Inklusive Netto-Urlaubstage-Berechnung (exkl. Wochenenden/Feiertage).
- **🚑 Events / Ambulanzdienste:** Aggressive Suche nach geplanten Sanitätsdiensten und Veranstaltungen über alle verfügbaren Abteilungen hinweg.
- **📒 Mitarbeiter-Verzeichnis:** Suche nach Kontaktdaten (Telefon, E-Mail), Rollen und Qualifikationen von Kollegen.
- **📺 Live-Monitor:** Echtzeit-Überwachung des Tagesplans mit automatischer Benachrichtigung bei Änderungen via Telegram.
- **🤖 Telegram Bot:** Integrierter Bot zur Fernabfrage von Dienstplänen und automatischen Versendung von PDF-Exporten.

## 🛠 Technische Details & Mechanismen

Das Tool nutzt modernste Techniken zur Datenextraktion und -verarbeitung:

### 1. Datenextraktion (Scraping & API)
Da das Portal keine öffentliche REST-API bietet, nutzt Incode CLI eine Kombination aus JSON-Endpunkten und direktem HTML-Parsing:
- **GUID Vacuuming:** Das Tool scannt Portalseiten nach 160-Bit Hex-Strings (GUIDs), um alle relevanten Organisations-IDs (OrgUnits) automatisch zu identifizieren.
- **HTML Parsing (BeautifulSoup):** Komplexe Ansichten wie das Projekt-Portal werden direkt aus dem DOM extrahiert, um Namen und freie Plätze ("Bedarf") anzuzeigen, die in den JSON-Antworten oft fehlen.
- **Request Chunking:** Um Server-Limits zu umgehen, werden Anfragen (z.B. für Event-Details) in Batches (max. 20-30 IDs) aufgeteilt.

### 2. Authentifizierung & Sicherheit
- **Session Management:** Nutzung von `requests.Session` mit persistierten Cookies und automatischem Re-Login bei Session-Ablauf.
- **Security Headers:** Extraktion und Nutzung von portal-spezifischen Sicherheits-Tokens (z.B. `x-incode-xxx`), die dynamisch aus JavaScript-Files oder dem Header geparst werden.
- **Lokale Verschlüsselung:** Zugangsdaten werden lokal in einer Konfigurationsdatei gespeichert (außerhalb der Git-Verwaltung).

### 3. Logik & Algorithmen
- **Timezone Handling:** Automatische Korrektur von Portal-Zeitstempeln basierend auf lokaler Systemzeit und Sommerzeit-Offsets.
- **Feiertags-Engine:** Implementierung des Gaußschen Oster-Algorithmus zur dynamischen Berechnung österreichischer Feiertage für die Netto-Urlaubsstatistik.
- **Event-Grouping:** Gruppierung von Projekt-Einträgen nach Triple-Keys `(ID, Start, Ende)`, um Serien-Events korrekt als Einzeltermine darzustellen.

## 📦 Installation

1. Repositorium klonen:
   ```bash
   git clone https://github.com/manueloberberger/incode-cli.git
   cd incode-cli
   ```

2. Virtuelle Umgebung erstellen und Abhängigkeiten installieren:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Anwendung starten:
   ```bash
   python3 incode.py
   ```

## 🏗 Projektstruktur

- `incode.py`: Haupteinstiegspunkt und Menüführung.
- `src/api.py`: Kernlogik für Portal-Kommunikation, Scraping und Datenverarbeitung.
- `src/ui.py`: Interaktive Menüs, Tabellendarstellungen (Rich) und Benutzerinteraktion.
- `src/bot.py`: Implementierung des Telegram Bots (python-telegram-bot).
- `src/pdf.py`: PDF-Generierung mittels ReportLab.
- `src/ical.py`: Export von Kalender-Dateien (ICS).
- `src/config.py`: Konfigurationsmanagement und Styling.

## 📝 Lizenz

Dieses Projekt ist für den internen Gebrauch beim Roten Kreuz bestimmt. Die Nutzung erfolgt auf eigene Gefahr.
