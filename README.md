# Incode CLI & Bot v1.3

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)
![Bot](https://img.shields.io/badge/bot-interactive-blue.svg)

Eine hochoptimierte CLI-Anwendung und ein intelligenter Telegram-Bot zur effizienten Interaktion mit dem **Incode-Dienstplansystem des Roten Kreuzes**.

**Neu in Version 1.3:** Der Telegram-Bot ist jetzt vollständig interaktiv! Navigiere durch Menüs, wähle Daten per Button-Klick und erhalte PDFs in Sekundenschnelle – ganz ohne kryptische Befehle.

---

## 🚀 Features

### 📱 Telegram Bot (v1.3)
Der Bot ist dein persönlicher Dienstplan-Assistent für die Hosentasche.
*   **Interaktives Menü:** Starte mit `/start` und steuere alles über Buttons.
*   **Smart Date Picker:**
    *   Klicke auf `📅 Anderes Datum`, um den Tagesplan für einen beliebigen Tag abzurufen.
    *   Nutze Schnellauswahl-Buttons für *Morgen* oder *Übermorgen*.
    *   Oder tippe einfach ein Datum ein (z.B. `15.1.` oder `24.12.`).
*   **PDF on Demand:** Egal ob *eigener Dienstplan* oder *Gesamttagesplan* – der Bot generiert sofort eine saubere PDF-Datei.
*   **Endlos-Modus:** Nach jeder Aktion bietet dir der Bot das Menü erneut an, damit du sofort weitermachen kannst.

### 🛠 Wartung & Komfort
*   **Auto-Update Check:** Das Tool prüft beim Start automatisch auf neue Versionen auf GitHub und benachrichtigt dich.
*   **Dependency Guard:** Startet das Tool nicht, weil Bibliotheken fehlen (z.B. nach einem Update)? Der `incode`-Startwrapper erkennt das sofort und zeigt dir den passenden Befehl zur Reparatur.

### 💻 Terminal CLI
Die mächtige Kommandozentrale für den PC:
*   **Smart Dashboard:** Zeigt sofort beim Start deine nächsten Dienste (dank lokalem Caching ohne Wartezeit).
*   **Live-Monitor:** Ein spezialisierter Modus für Wachen-Monitore.
    *   Aktualisiert sich selbstständig alle X Minuten.
    *   Erkennt Änderungen (z.B. Fahrzeugtausch) automatisch.
    *   Sendet bei Änderungen sofort ein PDF-Update an Telegram.
*   **Kollegen-Suche:** Finde heraus, wann und wo deine Kollegen Dienst haben.
*   **Exporte:**
    *   **PDF:** Mit Zeitstempel im Dateinamen (z.B. `Tagesplan_2026-01-08_14-30.pdf`).
    *   **iCal:** Standardkonforme Kalenderdateien für Outlook, Google & Apple.

---

## 🛠 Installation

### Voraussetzungen
*   **Python 3.8+**
*   Linux, macOS oder Windows

### Setup

1.  **Repository klonen:**
    ```bash
    git clone https://github.com/manueloberberger/incode-cli.git
    cd incode-cli
    ```

2.  **Installieren:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Starten:**
    ```bash
    # CLI starten
    ./incode

    # Bot direkt starten
    ./incode bot
    ```

*Beim ersten Start wirst du nach deinen Zugangsdaten gefragt. Diese werden lokal verschlüsselt in `.credentials.json` gespeichert.*

---

## 🤖 Bot Konfiguration

Um den Telegram-Bot zu nutzen:

1.  Schreibe [@BotFather](https://t.me/BotFather) auf Telegram und erstelle einen neuen Bot -> Du erhältst einen **Token**.
2.  Schreibe [@userinfobot](https://t.me/userinfobot), um deine persönliche **User ID** zu erhalten.
3.  Starte `./incode bot`. Das Tool fragt dich einmalig nach diesen Daten.

*Sicherheitshinweis: Der Bot antwortet NUR auf die konfigurierte User ID. Fremde Anfragen werden ignoriert.*

---

## 🧠 Technik & Architektur

*   **Hybrid Async Core:** Der Bot nutzt `python-telegram-bot` im asynchronen Modus für das UI, lagert aber die schweren API-Calls und das PDF-Rendering in Threads aus. Das garantiert ein flüssiges Button-Erlebnis ohne "Einfrieren".
*   **Smart Caching:** Um die Incode-Server zu entlasten und den Start zu beschleunigen, werden Dienstpläne lokal in `.incode_cache.json` zwischengespeichert (TTL: 15 Min).
*   **Reverse Engineering:** Da keine offizielle API existiert, emuliert das Tool einen Browser-Client (Session-Hijacking, Token-Extraction aus JS-Code).
*   **ReportLab Engine:** PDFs werden direkt im RAM gezeichnet (< 0.1s Generierungszeit), statt HTML umständlich zu konvertieren.

---

## 📂 Projektstruktur

```
incode-cli/
├── incode.py           # Entry Point & CLI Wrapper
├── .credentials.json   # Config (Git-Ignored)
├── .incode_cache.json  # Cache (Git-Ignored)
├── src/
│   ├── api.py          # Incode API Logic & Caching
│   ├── bot.py          # Telegram Bot Logic (Async/ConversationHandler)
│   ├── config.py       # Settings & Versioning
│   ├── ical.py         # iCal Generator
│   ├── pdf.py          # PDF Generator
│   └── ui.py           # CLI Interface (Rich)
└── requirements.txt    # Dependencies
```

---
*Hinweis: Dieses Tool ist ein Community-Projekt und steht in keiner offiziellen Verbindung zum Roten Kreuz.*