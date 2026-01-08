# Incode CLI 🚑

![Version](https://img.shields.io/badge/version-1.9.0-blue) ![Python](https://img.shields.io/badge/python-3.9%2B-green) ![Status](https://img.shields.io/badge/status-active-success)

**Incode CLI** ist ein hochperformantes, Terminal-basiertes Interface für das Dienstplansystem des Roten Kreuzes (Incode / StaffPortal). Es wurde entwickelt, um die langsame und oft unübersichtliche Weboberfläche durch eine schnelle, tastaturgesteuerte TUI (Terminal User Interface) zu ersetzen und bietet Funktionen, die im Originalsystem fehlen oder schwer zugänglich sind.

```text
   ___ _  _  ___  ___  ___  ___       ___ _    ___   
  |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  
   | || .  | (__| (_) | |) | _|     | (__| |__ | |   
  |___|_|\_|\___|\___/|___/|___|     \___|____|___|  
```

---

## 🛠 Technische Architektur

Das Projekt ist modular in Python aufgebaut und nutzt modernes Reverse Engineering, um mit der Incode-Backend-API zu kommunizieren.

### 1. API-Interface & Session Management (`src/api.py`)
Der Kern der Anwendung ist die `IncodeRequests` Klasse. Da es keine öffentliche API gibt, simuliert der Client einen vollwertigen Browser.

*   **Authentifizierung:** Der Login erfolgt via POST-Request an `/login.php`. Die Session-Cookies (`PHPSESSID`) werden persistiert.
*   **Header-Spoofing:** Das System verlangt dynamische Header. Der Client extrahiert reguläre Ausdrücke (`x-incode-*`) aus dem HTML/JS-Sourcecode der Startseite, um gültige Requests zu signieren.
*   **GUID Discovery:** Incode nutzt Global Unique IDs (GUIDs) für Organisationseinheiten und Projekte. Der Client scrapt diese GUIDs rekursiv (`StaffPortal/dispo.php`, `projects.php`) und speichert sie, um auch dienstellenübergreifende Abfragen zu ermöglichen.
*   **Caching:** Um die Latenz zu minimieren, werden API-Antworten (wie der Dienstplan) in `.incode_cache.json` mit einer TTL (Time To Live) von 15 Minuten gecacht.

### 2. Intelligente Datenverarbeitung

#### A. Abwesenheits-Logik & Feiertags-Matrix
Das Originalsystem liefert oft unklare Daten für "freie Tage" in Urlaubsblöcken. Incode CLI implementiert eine eigene Heuristik:
*   **Holiday-Engine:** Berechnet österreichische Feiertage (inkl. variabler Oster-Termine) dynamisch.
*   **Sandwich-Logik:** Ein Sonntag wird normalerweise als "Freies Wochenende" markiert. Die CLI prüft jedoch den Freitag davor und den Montag danach. Sind beide Urlaubstage, wird der Sonntag technisch korrekt als "Abwesend" (Urlaubsbestandteil) klassifiziert.
*   **Priorisierung:** Echte Abwesenheiten (Krank, Urlaub, Pflegefreistellung) überschreiben immer generische "Frei"-Marker.

#### B. Mitarbeiter-Verzeichnis & Deduplizierung
Die Suche (`search_staff_contact`) aggregiert Daten aus *allen* verfügbaren Organisationseinheiten.
*   **Merge-Algorithmus:** Mitarbeiter existieren oft doppelt (einmal im Stammbezirk mit PNR, einmal im Gastbezirk ohne PNR).
*   **Scoring:** Ein heuristisches Scoring-System bewertet jeden Datensatz (Punkte für vorhandene Telefonnummer, E-Mail, zugewiesene Rollen). Dubletten werden basierend auf Name und PNR zusammengeführt, wobei immer der Datensatz mit dem höchsten "Informationsgehalt" gewinnt.

### 3. User Interface (`src/ui.py`)
Das UI basiert auf der `rich` Library für modernes Terminal-Rendering.
*   **Responsive Layouts:** Tabellen und Panels passen sich dynamisch der Terminalbreite an.
*   **Live Monitor:** Ein Loop fragt in einstellbaren Intervallen den Tagesplan ab und aktualisiert die Ansicht bei Änderungen sofort (Polling).

### 4. Telegram Bot Integration (`src/bot.py`)
Ein asynchroner Bot (basierend auf `python-telegram-bot`) läuft im Hintergrund oder als Standalone-Modus.
*   Er fungiert als Bridge, um generierte PDFs (Dienstpläne) direkt an das Smartphone des Users zu pushen.
*   Nutzt die gleiche API-Instanz wie die CLI, spart somit erneute Logins.

---

## 🚀 Features

*   **Dienstplan-Übersicht:** Zukünftige Dienste, inkl. Statistik (Stunden pro Monat, Dienste pro Typ).
*   **Tagesplan (Live):** Echtzeit-Ansicht aller Fahrzeuge und Besatzungen des aktuellen Tages.
*   **PDF & iCal Export:** Generiert saubere PDFs (`reportlab`) und Kalenderdateien (`icalendar`) für den Import in Google/Apple Kalender.
*   **Mitarbeiter-Suche:** Detaillierte Infos (Telefon, Skills, Gruppen, Salden) mit intelligenter Zusammenführung.
*   **Auto-Update:** Selbst-aktualisierend via Git (`src/utils.py`), inkl. Stash-Schutz für lokale Änderungen.

---

## 📦 Installation & Setup

### Voraussetzungen
*   Python 3.9 oder höher
*   Git

### Schritt-für-Schritt

1.  **Repository klonen:**
    ```bash
    git clone https://github.com/DEIN_USER/incode-cli.git
    cd incode-cli
    ```

2.  **Abhängigkeiten installieren:**
    Es wird empfohlen, ein Virtual Environment zu nutzen.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Starten:**
    ```bash
    python3 incode.py
    ```
    *Beim ersten Start fragt die CLI nach deinen Zugangsdaten (Benutzername/Passwort) und speichert diese lokal verschlüsselt (chmod 600) in `.credentials.json`.*

---

## 🔧 Konfiguration

Die Konfiguration liegt in `src/config.py` und `.credentials.json`.
*   **credentials.json:** Speichert Auth-Token und die `allowed_user_id` für den Telegram Bot.
*   **Themes:** Farben für die TUI können in `src/config.py` im `theme`-Objekt angepasst werden.

---

## ⚠️ Disclaimer

Dieses Tool ist **keine offizielle Software** des Roten Kreuzes oder der Incode GmbH. Es handelt sich um ein privates Hobby-Projekt zur Verbesserung der Usability für Mitarbeiter. Die Nutzung erfolgt auf eigene Gefahr.

---

*Developed with ❤️ & ☕ by Manuel Oberberger*