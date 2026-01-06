# Incode CLI v1.0

Eine hochoptimierte CLI-Anwendung und ein automatisierter Telegram-Bot zur effizienten Interaktion mit dem **Incode-Dienstplansystem des Roten Kreuzes**.

Dieses Projekt vereint die Funktionalitäten eines interaktiven Terminals mit der Mobilität eines Telegram-Bots. Es wurde entwickelt, um Sanitätern und Führungskräften einen schnellen, gefilterten und übersichtlichen Zugriff auf Einsatzpläne zu ermöglichen – ohne die oft träge Weboberfläche nutzen zu müssen.

## 🚀 Kernfunktionen

### 1. Interaktives Terminal-Interface (CLI)
Das CLI ist das Herzstück für die stationäre Nutzung (z.B. auf der Dienststelle oder am PC):
- **Dashboard:** Eine kompakte Übersicht deiner nächsten Dienste direkt beim Start.
- **Tagesplan-Explorer:** Durchsuche den gesamten Dienstplan für heute oder ein beliebiges Datum. Sieh sofort, welche Fahrzeuge (RTW, KTW, NEF etc.) besetzt sind und wer die Besatzung bildet.
- **Live-Monitor:** Ein spezialisierter Modus, der den Plan in Echtzeit (Auto-Refresh) anzeigt – ideal für einen Monitor in der Fahrzeughalle oder im Aufenthaltsraum.
- **Intelligente Suche:** Suche nach Kollegen, um deren Einteilungen zu sehen (praktisch für die Dienstübergabe oder zum Finden von Tauschpartnern).
- **Daten-Export:** Generiere PDF-Übersichten oder iCal-Dateien für deinen persönlichen Kalender.

### 2. Telegram Bot (Mobile Access)
Der Bot dient als dein persönlicher Assistent für die Hosentasche:
- **On-Demand PDF:** Sende `/dienste` oder `/tagesplan` an den Bot und erhalte innerhalb von Sekunden ein fertig formatiertes PDF-Dokument.
- **Sicherheit:** Der Bot reagiert nur auf deine spezifische Telegram User-ID (Whitelist-Prinzip).
- **Effizienz:** Statt hunderte Zeilen Text zu scrollen, bietet das PDF eine druckreife und professionelle Tabellenansicht.

### 3. Technische Highlights
- **Smart Scraper:** Die API-Schnittstelle (`src/api.py`) nutzt eine hybride Methode aus JSON-API-Abfragen und intelligentem HTML-Parsing, um auch bei unterschiedlichen Incode-Konfigurationen zuverlässig Daten zu liefern.
- **Deduplizierung:** Automatische Bereinigung von Doppeleinträgen und Zusammenführung von Archiv- und Zukunftsdaten.
- **Sicherheit:** Zugangsdaten werden lokal verschlüsselt bzw. mit restriktiven Dateirechten (`chmod 600`) in `.credentials.json` gespeichert. Keine Daten verlassen dein System außer in Richtung der offiziellen Incode-Server und der Telegram-API.

## 🛠 Installation & Setup

### Voraussetzungen
- Ein Computer mit **Linux** oder **macOS** (Windows via WSL möglich).
- **Python 3.8** oder neuer.

### Schritt-für-Schritt

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
   ```

3. **Starten:**
   ```bash
   chmod +x incode
   ./incode
   ```

### Optional: Globaler Befehl
Damit du das Tool von überall aufrufen kannst (ohne immer in den Ordner zu wechseln), erstelle einen Link:
```bash
ln -sf $(pwd)/incode ~/.local/bin/incode
# Dann einfach tippen: incode
```

## 📖 Nutzungshilfen

### CLI Befehle
Im Hauptmenü navigierst du einfach mit den Pfeiltasten oder durch Eingabe der entsprechenden Ziffern.
- `Live-Monitor`: Startet eine Endlosschleife. Beenden mit `Strg + C`.
- `Tagesplan`: Datumseingabe im Format `TT.MM.JJJJ` oder einfach Enter für heute.

### Telegram Befehle
- `/start`: Zeigt die verfügbaren Optionen.
- `/dienste`: Generiert ein PDF mit all deinen zukünftigen Diensten.
- `/tagesplan`: Generiert ein PDF des heutigen Gesamtfahrzeugplans.

## ⚙️ Konfiguration
Beim ersten Start fragt das Tool nach:
- **Incode-User:** Dein Standard-Login (meist die Personalnummer).
- **Incode-Passwort:** Dein Passwort (wird sicher maskiert).
- **Telegram Token:** (Optional) Falls du den Bot nutzen möchtest, von [@BotFather](https://t.me/botfather).
- **User ID:** Deine Telegram ID (erhältst du z.B. über [@userinfobot](https://t.me/userinfobot)).

---
*Hinweis: Dieses Tool steht in keiner offiziellen Verbindung zum Roten Kreuz. Es nutzt die öffentlich zugänglichen Web-Schnittstellen des Dienstplansystems.*