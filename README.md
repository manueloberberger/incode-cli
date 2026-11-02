# Incode CLI

Tastaturgesteuerte Terminal-Anwendung für Incode-Dienstpläne des Österreichischen Roten Kreuzes – mit mehreren Konten, Statistiken, Exporten und Telegram-Bot.

![Projektbanner](.github/banner.png)

[![Version](https://img.shields.io/badge/version-2.32.1-blue.svg)](CHANGELOG.md) ![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg) [![MIT-Lizenz](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](LICENSE)

**macOS und Linux · Python 3.9+ · Berechtigtes Incode-Konto für eigene Dienstplandaten**

## Funktionen

- Persönlichen Dienstplan und Tagesplan mit Suche, Filtern und Tastaturbedienung anzeigen.
- Mehrere Konten verwalten und bewusst zwischen ihnen wechseln.
- Geleistete und geplante Stunden getrennt auswerten.
- Dienste als PDF oder Kalenderdatei exportieren und lokale Daten exportieren/importieren.
- Dienständerungen überwachen und optional per Telegram melden.
- Hintergrundbetrieb über launchd auf macOS oder systemd auf Linux.
- Git-basierte Selbstaktualisierung bei sauberem Arbeitsverzeichnis.

## Installation

Benötigt werden Python 3.9+, Git, eine Shell und die vom Installer geprüften Systemwerkzeuge. Für Plattformdetails siehe [COMPATIBILITY.md](COMPATIBILITY.md).

```sh
git clone https://github.com/manueloberberger/incode-cli.git
cd incode-cli
./install.sh
```

Der Installer richtet eine virtuelle Python-Umgebung und den Befehl `incode` unter `~/.local/bin` ein. Falls nötig, diesen Ordner zum PATH der eigenen Shell hinzufügen:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Alternativ steht [quick-install.sh](quick-install.sh) für die Installation unter `~/.local/share/incode-cli` bereit. Das Skript vor dem Ausführen prüfen. Zur Deinstallation dient `./uninstall.sh`; die Nachfrage zur Entfernung persönlicher Zugänge bewusst beantworten.

## Erster Start und Konten

```sh
incode
# Im Projektverzeichnis alternativ:
./incode
```

Beim ersten Start ein Konto einrichten. **Benutzer wechseln** wählt ein bestehendes Profil; **Neuen Benutzer hinzufügen** ergänzt ein weiteres.

```sh
./incode --select
./incode --user "Profilname"
```

## Dienstplan, Statistik und Export

In **Mein Dienstplan** öffnet **F** die Filter für abgeschlossene, geplante/laufende Dienste sowie Monat und Jahr. **R** lädt erneut vom Server. PDF- und Kalenderexport verwenden die sichtbare Filterauswahl.

Statistiken beziehen sich auf die tatsächlich geladenen Daten, nicht automatisch auf ein vollständiges Jahr. Dienste werden dem Startmonat zugerechnet; abgeschlossene und geplante Stunden bleiben getrennt. Die Dienstart berücksichtigt ausdrückliche Bezeichnungen und die implementierten Dienststellen-/Fahrzeugregeln; unklare Angaben bleiben unbekannt, ihre Stunden werden trotzdem gezählt.

Kalenderexport ist eine Dateiübertragung und keine laufende Synchronisation. Serverseitige Dienstkennungen bleiben bis zum Export erhalten. Fehlt eine Kennung, kann eine Änderung von Zeit, Fahrzeug oder Ort eine neue Kalenderidentität erzeugen. Lokale Kalenderzeiten verwenden Europe/Vienna, Exportzeitstempel UTC.

## Telegram-Bot

Zuerst einen eigenen Telegram-Bot und die erlaubte Benutzer-ID einrichten. Der interaktive Start fragt die nötigen Angaben ab:

```sh
./incode bot
./incode bot --user "Profilname"
```

Für dauerhaften Hintergrundbetrieb nach erfolgreicher Einrichtung:

```sh
./incode install-service --user "Profilname"
```

Der Dienst verwendet systemd beziehungsweise launchd. Ein laufender Prozess bestätigt noch keine erfolgreiche Anmeldung oder Zustellung. Dienständerungen umfassen unter anderem Besatzung, Dienststelle, Zeiten, Fahrzeug und Kommentare. Ein neuer Überwachungssnapshot wird zunächst ohne Änderungsalarm initialisiert.

## Daten, Verbindungen und Updates

Konten, Einstellungen, Cache und Botzustände werden lokal in SQLite verwaltet. Gespeicherte Passwörter und Bot-Tokens sind keine verschlüsselte Schlüsselbundablage. Datenbanken, Logs, Exporte und Sicherungen vertraulich behandeln und nicht in Git übernehmen.

Netzwerkaufrufe haben Zeitlimits. Fehlerhafte oder unvollständige Antworten werden nicht als leerer gültiger Dienstplan ausgegeben. Ansichten kennzeichnen Cache-Daten beziehungsweise bieten erneutes Laden an; der Live-Monitor behält bei Fehlern die letzte gültige Anzeige.

Selbstupdates benötigen einen sauberen Checkout einschließlich unversionierter Dateien. Eigene Änderungen vorher bewusst sichern oder committen. Der Updater führt kein automatisches Stash aus.

## Entwicklung und Prüfung

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m mypy --strict incode.py src/
./test-compatibility.sh
```

| Bereich | Einstieg |
| --- | --- |
| Start und Terminaloberfläche | `incode.py`, `src/ui/` |
| HTTP und synchrone Fassade | `src/api_async.py`, `src/api.py` |
| Speicherung und Parsing | `src/db.py`, `src/parser.py` |
| Bot und Hintergrunddienst | `src/bot.py`, `src/service.py` |
| Sicherung und Updates | `src/backup.py`, `src/updates.py` |

Tests prüfen definierte Fälle und ersetzen keine Prüfung gegen ein verändertes Incode-Portal. Keine echten Zugangsdaten oder persönlichen Dienstpläne als Testfixtures verwenden.

## Weitere Informationen

[Änderungen](CHANGELOG.md) · [Kompatibilität](COMPATIBILITY.md) · [Mitwirken](CONTRIBUTING.md) · [MIT-Lizenz](LICENSE) · [Historische README](README-ARCHIV.md)
