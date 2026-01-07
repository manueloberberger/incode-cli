# Incode CLI & Bot v1.6

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)
![Bot](https://img.shields.io/badge/bot-interactive-blue.svg)

Eine hochoptimierte CLI-Anwendung und ein intelligenter Telegram-Bot zur effizienten Interaktion mit dem **Incode-Dienstplansystem des Roten Kreuzes**.

**Neu in Version 1.6:** Optimiertes **Mitarbeiter-Verzeichnis**. Suche Kollegen jetzt auch direkt über ihre Dienstnummer. Die Ergebnis-Anzeige wurde komplett überarbeitet, optisch aufpoliert und bietet nun noch mehr Details (Erstellungsdatum, Ursprung, Maportal-Rolle) bei besserer Übersichtlichkeit.

---

## 🚀 Kern-Features

### 📒 Mitarbeiter-Verzeichnis (Optimiert in v1.6)
Ein mächtiges Werkzeug, um schnell Kontaktinformationen oder Details zu Kollegen zu finden.
*   **Erweiterte Suche:** Finde Personen über:
    *   Namen (z.B. "Oberberger")
    *   Personalnummer (PNR)
    *   **NEU:** Dienstnummer (z.B. "2067" aus dem Berufstitel)
    *   E-Mail oder Telefonnummer
*   **Detail-Dashboard 2.0:** Komplett neu designte, übersichtliche Darstellung:
    *   **Basisdaten:** Dienstnummer, Incode-ID, Telefon, E-Mail, Salden (Urlaub/ZA).
    *   **Laufbahn & Rollen:** Schön formatierte Tabelle aller beruflichen Stationen und Rollen mit exakten Laufzeiten.
    *   **Qualifikationen & Gruppen:** Übersichtliche Tabellen mit IDs und Gültigkeitszeiträumen für alle Skills und Gruppenmitgliedschaften.
    *   **Meta-Daten:** Erstellungsdatum des Profils, letzter Login, Ursprung des Datensatzes.
*   **Raw-Data Mode:** Für Technik-Enthusiasten gibt es per Tastendruck (`r`) den vollständigen JSON-Datensatz direkt aus der Incode-API zur Ansicht.

### 📱 Der Telegram-Bot
Dein persönlicher Dienstplan-Assistent, der 24/7 erreichbar ist. Er wurde entwickelt, um die wichtigsten Informationen mit minimalem Datenverbrauch und maximaler Geschwindigkeit bereitzustellen.

*   **Vollständig Interaktiv:** Starte die Konversation einfach mit `/start`. Intuitive Buttons führen dich durch alle Funktionen – kein Auswendiglernen von Befehlen nötig.
*   **Intelligente Datumsauswahl (Smart Date Picker):**
    *   **Schnellwahl:** Buttons für *Heute*, *Morgen* oder *Übermorgen*.
    *   **Kalender-Funktion:** Über den Button `📅 Anderes Datum` kannst du gezielt Pläne für die Zukunft abrufen.
    *   **Natürliche Eingabe:** Sende einfach ein Datum wie `15.1.` oder `24.12.` an den Bot, um den entsprechenden Plan zu sehen.
*   **PDF-Generierung on Demand:**
    *   **Eigener Dienstplan:** Erstelle eine übersichtliche PDF deiner kommenden Dienste.
    *   **Gesamttagesplan:** Exportiere den kompletten Stations-Tagesplan als PDF für den schnellen Überblick offline.
*   **Sicherheits-Fokus:** Der Bot reagiert ausschließlich auf deine hinterlegte Telegram User-ID. Anfragen von Fremden werden ignoriert und geloggt.

### 💻 Die Terminal CLI (Kommandozeile)
Die mächtige Zentrale für Power-User und Wachen-Rechner:

*   **Echtzeit-Dashboard:** Zeigt dir sofort beim Start deine nächsten Dienste an. Durch intelligentes Caching geschieht dies ohne jegliche Verzögerung.
*   **Live-Monitor Modus:** Ideal für Monitore in der Wache oder in der Fahrzeughalle.
    *   **Auto-Refresh:** Aktualisiert die Daten selbstständig in konfigurierbaren Intervallen.
    *   **Change-Detection:** Erkennt Änderungen im Dienstplan (z.B. kurzfristiger Fahrzeugtausch oder Personaländerungen) sofort.
    *   **Push-Benachrichtigungen:** Sendet bei relevanten Änderungen automatisch eine Benachrichtigung inkl. aktualisiertem PDF an deinen Telegram-Bot.
*   **Gemeinsame Dienste:** Finde heraus, wann du mit bestimmten Kollegen gemeinsam Dienst hast ("Wann fahre ich wieder mit Max?").
*   **Export-Optionen:**
    *   **PDF-Export:** Professionell formatierte Pläne mit automatischem Zeitstempel (z.B. `Tagesplan_2026-01-08_14-30.pdf`).
    *   **iCal-Synchronisation:** Generiert `.ics` Dateien, die du direkt in Outlook, Google Calendar oder Apple Calendar importieren kannst.

### 🛠 Wartung & Komfort
*   **Auto-Update Check:** Das Tool prüft bei jedem Start, ob auf GitHub eine neue Version vorliegt, und informiert dich diskret.
*   **Dependency Guard:** Falls nach einem Update neue Python-Bibliotheken fehlen, erkennt der Startwrapper dies sofort und bietet dir den exakten Befehl zur Reparatur an, statt einfach mit einem Fehler abzustürzen.

---

## 🛠 Installation & Setup

### Voraussetzungen
*   **Python 3.8 oder höher**
*   Funktioniert auf Windows, macOS und Linux.

### Schritt-für-Schritt Installation

1.  **Repository klonen:**
    ```bash
    git clone https://github.com/manueloberberger/incode-cli.git
    cd incode-cli
    ```

2.  **Virtuelle Umgebung erstellen & Abhängigkeiten installieren:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Unter Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Die Anwendung starten:**
    ```bash
    # Für die interaktive CLI:
    ./incode

    # Um direkt den Telegram-Bot zu starten:
    ./incode bot
    ```

*Hinweis: Beim ersten Start wirst du nach deinen Incode-Zugangsdaten gefragt. Diese werden sicher und lokal verschlüsselt in der Datei `.credentials.json` abgelegt.*

---

## 🤖 Telegram-Bot Konfiguration

Um deinen privaten Bot einzurichten, folge diesen drei einfachen Schritten:

1.  **Bot erstellen:** Suche auf Telegram nach [@BotFather](https://t.me/BotFather) und sende `/newbot`. Du erhältst am Ende einen **API-Token**.
2.  **User-ID ermitteln:** Suche nach [@userinfobot](https://t.me/userinfobot), um deine numerische **User ID** zu erfahren. Nur diese ID erhält Zugriff auf deinen Bot.
3.  **Einrichtung abschließen:** Starte `./incode bot`. Das Programm wird dich nach dem Token und deiner ID fragen und diese für die Zukunft speichern.

### 💡 Tipp: Bot als System-Dienst (Linux)
Für den 24/7 Betrieb auf einem Server oder Raspberry Pi kann der Bot als `systemd` Service eingerichtet werden. Eine Anleitung dazu findest du in der Dokumentation oder frage den Entwickler.

---

## 🧠 Technik & Architektur

*   **Hybrid Async Core:** Der Bot nutzt das `python-telegram-bot` Framework im asynchronen Modus. Zeitintensive Aufgaben wie PDF-Rendering oder API-Abfragen werden in separate Worker-Threads ausgelagert, damit das User-Interface niemals blockiert.
*   **Smart Caching Engine:** Um die Last auf den Incode-Servern zu minimieren, werden Daten in der `.incode_cache.json` mit einer Time-to-Live (TTL) von 15 Minuten zwischengespeichert.
*   **High-Speed PDF Rendering:** Statt schwerfälliger HTML-zu-PDF Konverter nutzt Incode-CLI die `ReportLab`-Engine. PDFs werden direkt im Arbeitsspeicher gezeichnet und sind in weniger als 100ms bereit für den Versand.
*   **Reverse Engineering:** Da keine offizielle API existiert, emuliert das Tool die Anfragen eines Webbrowsers. Neue Features wie das Mitarbeiter-Verzeichnis nutzen undokumentierte Endpunkte (`getStaff.json`), um Daten zu aggregieren, die im Web-Frontend oft über mehrere Seiten verteilt sind.

---

## 📂 Projektstruktur

```text
incode-cli/
├── incode.py           # Haupt-Entrypoint & CLI-Logik
├── .credentials.json   # Verschlüsselte Zugangsdaten (wird nicht hochgeladen)
├── .incode_cache.json  # Lokaler Datencache (wird nicht hochgeladen)
├── src/
│   ├── api.py          # Kommunikation mit dem Incode-Backend & Caching
│   ├── bot.py          # Telegram-Bot Logik (Async/ConversationHandler)
│   ├── config.py       # Globale Einstellungen, Themes & Versionierung
│   ├── ical.py         # Logik für den iCal/Kalender-Export
│   ├── pdf.py          # ReportLab-Engine für PDF-Generierung
│   └── ui.py           # Rich-basiertes Terminal Interface
└── requirements.txt    # Erforderliche Python-Bibliotheken
```

---

## ⚖️ Rechtlicher Hinweis
Dieses Tool ist ein privates Community-Projekt. Es steht in **keiner offiziellen Verbindung** zum Roten Kreuz. Die Nutzung erfolgt auf eigene Gefahr. Bitte gehe verantwortungsbewusst mit deinen Zugangsdaten um.

---
*Entwickelt mit ❤️ für effizientes Dienstplan-Management.*