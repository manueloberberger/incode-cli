# Incode CLI - Rotes Kreuz Dienstplan Tool 🚑

Ein interaktives Kommandozeilen-Tool (CLI) für den Zugriff auf das Incode/Maportal Dienstplan-System (Rotes Kreuz).

## ✨ Features

*   **📅 Mein Dienstplan:** Übersicht aller kommenden Dienste mit Details zu Fahrzeug und Besatzung.
*   **🌴 Meine Abwesenheiten (BETA):** Detaillierte Liste aller Urlaube, freien Wochenenden und Feiertage.
    *   **Intelligente Logik:** Erkennt Feiertage in Urlaubsblöcken ("Geplante Sonderabwesenheit").
    *   **Lückenlos:** Ergänzt automatisch fehlende Sonntage nach Urlaubswochen.
    *   **Vorschau:** Zeigt genehmigte Wünsche an, auch wenn sie noch nicht fix im Dienstplan stehen (`[Gen. / n. eingetr.]`).
    *   **Urlaubs-Saldo:** Berechnet die tatsächlichen Netto-Urlaubstage (ohne Sonn-/Feiertage).
*   **🚑 Tagesplan:** Wer fährt heute wo? Live-Ansicht der Dienststelle mit Fahrzeugen und Besatzung.
*   **📺 Live-Monitor:** Automatisch aktualisierende Ansicht für Infoscreens in der Dienststelle.
*   **📒 Mitarbeiter-Suche:** Schnelles Finden von Kontaktdaten, Dienstnummern und Qualifikationen von Kollegen.
*   **🔍 Gemeinsame Dienste:** Finde heraus, wann du mit einer bestimmten Person Dienst hast.
*   **📤 Export:**
    *   **PDF:** Sauber formatierte Dienstpläne zum Ausdrucken oder Versenden.
    *   **iCal:** Export für deinen digitalen Kalender (Google, Outlook, etc.).
*   **🤖 Telegram Bot:** Integrierter Bot, um Dienstpläne und Updates direkt aufs Handy zu bekommen.

## 🚀 Installation

Voraussetzung: Python 3.8 oder neuer.

1.  Repository klonen:
    ```bash
    git clone https://github.com/manueloberberger/incode-cli.git
    cd incode-cli
    ```

2.  Abhängigkeiten installieren (am besten in einem Virtual Environment):
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

## 🎮 Benutzung

Starte das Tool einfach über:
```bash
python3 incode.py
```

### Erste Schritte
Beim ersten Start wirst du nach deinen Zugangsdaten gefragt:
1.  **Benutzername** (Incode Login)
2.  **Passwort**

Diese Daten werden lokal und sicher (Dateirechte 600) in einer `.credentials.json` gespeichert.

### Steuerung
*   Nutze die **Pfeiltasten** (⬆/⬇), um im Menü zu navigieren.
*   Bestätige mit **Enter** (↵).
*   Gehe zurück oder beende das Programm mit **ESC** oder **q**.

## 🛠️ Technische Details

*   **Version:** 1.7
*   **Cache:** Um die Serverlast zu minimieren und die Geschwindigkeit zu erhöhen, werden Daten kurzzeitig (15 Min) lokal in `.incode_cache.json` zwischengespeichert.
*   **Export:** PDF-Dateien werden im aktuellen Verzeichnis gespeichert.

## ⚠️ Disclaimer

Dies ist ein inoffizielles Tool. Es steht in keiner direkten Verbindung zum Roten Kreuz oder den Entwicklern der Incode-Software. Nutzung auf eigene Verantwortung.
