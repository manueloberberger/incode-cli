# Incode CLI & Bot v1.4

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)
![Bot](https://img.shields.io/badge/bot-interactive-blue.svg)

Eine hochoptimierte CLI-Anwendung und ein intelligenter Telegram-Bot zur effizienten Interaktion mit dem **Incode-Dienstplansystem des Roten Kreuzes**.

**Neu in Version 1.4:** Automatische Update-Prüfung und intelligenter Dependency-Check beim Start. Der Telegram-Bot ist weiterhin vollständig interaktiv und bietet verbesserte Stabilität.

---

## 🚀 Kern-Features

### 📱 Der Telegram-Bot (v1.4)
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
*   **Umfangreiche Suche:** Finde schnell heraus, wann Kollegen Dienst haben, um Dienste zu tauschen oder Fahrgemeinschaften zu bilden.
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

---

## 🧠 Technik & Architektur

*   **Hybrid Async Core:** Der Bot nutzt das `python-telegram-bot` Framework im asynchronen Modus. Zeitintensive Aufgaben wie PDF-Rendering oder API-Abfragen werden in separate Worker-Threads ausgelagert, damit das User-Interface niemals blockiert.
*   **Smart Caching Engine:** Um die Last auf den Incode-Servern zu minimieren, werden Daten in der `.incode_cache.json` mit einer Time-to-Live (TTL) von 15 Minuten zwischengespeichert.
*   **High-Speed PDF Rendering:** Statt schwerfälliger HTML-zu-PDF Konverter nutzt Incode-CLI die `ReportLab`-Engine. PDFs werden direkt im Arbeitsspeicher gezeichnet und sind in weniger als 100ms bereit für den Versand.
*   **Sicherheit:** Alle sensiblen Daten verbleiben lokal auf deinem Rechner. Es findet keine Übertragung an Drittserver statt (außer direkt zu Incode und Telegram).

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
