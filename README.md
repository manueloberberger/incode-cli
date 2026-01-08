# Incode CLI 🚑

![Version](https://img.shields.io/badge/version-1.9.0-blue) ![Python](https://img.shields.io/badge/python-3.9%2B-green) ![Status](https://img.shields.io/badge/status-active-success)

**Incode CLI** ist das ultimative Power-User-Tool für das Dienstplansystem des Roten Kreuzes. Es ersetzt die träge Weboberfläche durch ein blitzschnelles Terminal-Interface und erweitert das System um intelligente Funktionen, Analysen und Automatisierungen, die im Standard-Client nicht existieren.

```text
   ___ _  _  ___  ___  ___  ___       ___ _    ___   
  |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  
   | || .  | (__| (_) | |) | _|     | (__| |__ | |   
  |___|_|\_|\___|\___/|___/|___|     \___|____|___|  
```

---

## ✨ Haupt-Features im Detail

### 📅 Next-Gen Dienstplan & Statistik
Vergiss unübersichtliche Monatsansichten. Incode CLI liefert dir genau das, was zählt.
*   **Klare Listenansicht:** Alle zukünftigen Dienste, sortiert und gefiltert.
*   **Integrierte Analytics:** Das Tool berechnet automatisch:
    *   **Stunden-Statistik:** Summiert deine Dienststunden pro Monat.
    *   **Dienst-Typen:** Wie oft fährst du RTW vs. KTW?
    *   **Dienststellen:** Wo bist du am häufigsten eingeteilt?
*   **Team-Radar:** Suche nach Diensten, die du gemeinsam mit einem bestimmten Kollegen fährst (`🔍 Gemeinsame Dienste`).

### 👥 Intelligentes Mitarbeiter-Verzeichnis
Die mächtigste Funktion der CLI. Das System durchsucht nicht nur deine Stammdienststelle, sondern **alle** verknüpften Organisationseinheiten.
*   **Cross-District Search:** Findet Kollegen auch in anderen Bezirken, wo sie z.B. nur gastweise tätig sind.
*   **Auto-Merge Algorithmus:** Das System erkennt Duplikate (z.B. User einmal mit PNR, einmal ohne) und verschmilzt sie zu einem einzigen, vollständigen "Golden Record".
*   **Detail-View (Taste 'd'):**
    *   Zeigt formatierte Telefonnummern (mobil/privat) und Adressen.
    *   Listet alle Qualifikationen (NFS, NK, Fahrerlaubnis...) und Gruppenzugehörigkeiten.
    *   **Live-Salden:** Zeigt den aktuellen Urlaubs- und Zeitausgleichs-Saldo farblich codiert (Grün/Rot) an.

### 🌴 Smartes Abwesenheits-Management
Das System korrigiert die oft fehlerhafte Darstellung von "freien Tagen" im Web-Portal.
*   **Netto-Urlaubstage:** Berechnet exakt, wie viele Urlaubstage eine Abwesenheit tatsächlich "kostet" (exklusive Wochenenden und Feiertage).
*   **Sandwich-Logik:** Erkennt automatisch, ob ein Sonntag ein "echter" freier Tag ist oder Teil eines durchgehenden Urlaubsblocks (wichtig für die Abrechnung).
*   **Feiertags-Engine:** Kennt alle österreichischen Feiertage inkl. variabler Ostertermine bis in die Zukunft.

### 🏥 Live-Monitor & Tagesplan
Für die Leitstelle oder den Wachen-Monitor.
*   **Echtzeit-Ansicht:** Zeigt alle Fahrzeuge und Besatzungen des heutigen Tages.
*   **Auto-Refresh:** Aktualisiert die Ansicht automatisch alle X Minuten.
*   **Telegram-Alerts:** Kann bei Änderungen im Tagesplan (z.B. Krankmeldung -> Umbesetzung) sofort ein PDF in deinen Telegram-Chat pushen.

### 📤 Export & Synchronisation
*   **PDF-Generator:** Erstellt saubere, druckfertige Dienstpläne direkt im Terminal.
*   **iCal-Sync:** Exportiert deine Dienste als `.ics` Datei für den direkten Import in Google Calendar, Outlook oder Apple Kalender.
*   **Telegram-Push:** Sende dir den aktuellen Plan mit einem Tastendruck (`t`) direkt aufs Handy.

---

## 🛠 Unter der Haube (Technical Deep Dive)

Das Projekt ist modular in Python aufgebaut und nutzt Reverse Engineering, um direkt mit dem Incode-Backend zu kommunizieren.

### API & Session Management (`src/api.py`)
Da Incode keine öffentliche API besitzt, emuliert die CLI einen vollwertigen Browser-Client.
*   **Header-Spoofing:** Extrahiert dynamische Security-Token (`x-incode-*`) mittels RegEx aus dem JavaScript-Quelltext der Login-Seite.
*   **GUID Discovery:** Scrapt rekursiv alle verfügbaren Organisations-GUIDs (`orgUnitDataGuid`), um Zugriff auf Daten außerhalb der eigenen Stamm-Dienststelle zu erhalten.
*   **Performance Caching:** Speichert API-Responses (`.incode_cache.json`) mit einer TTL von 15 Minuten, um Latenzen bei wiederholten Abfragen zu eliminieren.

### UI Architektur (`src/ui.py`)
Basierend auf der `rich` Library für modernes TUI-Rendering.
*   **Responsive Layouts:** Tabellen und Panels passen sich dynamisch der Terminalbreite an.
*   **Event Loop:** Tastatur-Inputs werden plattformübergreifend (Windows `msvcrt` / Unix `termios`) abgefangen, um eine App-ähnliche Navigation zu ermöglichen.

### Robustes Auto-Update (`src/utils.py`)
Die CLI hält sich selbst aktuell.
*   **Git Stash Protection:** Vor einem Update prüft das System auf lokale Änderungen, sichert diese (`git stash`), zieht das Update (`git pull`), installiert neue Abhängigkeiten (`pip install`) und stellt die Änderungen wieder her (`git stash pop`).

---

## 📦 Installation

### Voraussetzungen
*   Python 3.9+
*   Git

### Quick Start

1.  **Klonen:**
    ```bash
    git clone https://github.com/DEIN_USER/incode-cli.git
    cd incode-cli
    ```

2.  **Setup:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Start:**
    ```bash
    python3 incode.py
    ```
    *(Deine Zugangsdaten werden beim ersten Start lokal und sicher gespeichert.)*

---

## ⚠️ Disclaimer

Dieses Tool ist **keine offizielle Software** des Roten Kreuzes oder der Incode GmbH. Es ist ein privates Open-Source Projekt zur Verbesserung der Usability und Effizienz. Nutzung auf eigene Gefahr.

---

*Developed with ❤️ & ☕ by Manuel Oberberger*
