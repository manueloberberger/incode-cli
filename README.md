# Incode CLI 🚑

[![Version](https://img.shields.io/badge/version-2.9.0-blue.svg)](https://github.com/manueloberberger/incode-cli)?label=version&style=flat-square) ![Python](https://img.shields.io/badge/python-3.9%2B-green?style=flat-square)

**The lightning-fast, keyboard-driven interface for the Red Cross duty roster.**

---

## 🔄 Changelog

### v2.9.0 (Latest)
- **PDF Export**: "Meine Abwesenheiten" können nun als PDF exportiert werden (`p`-Taste).
- **Telegram Cleanup**: Versendete PDFs werden nach dem Upload automatisch gelöscht.
- **UX**: Lade-Animation beim Login ("Melde an...").
- **Bot**: Graceful Handling wenn der Bot auf einem anderen Gerät gestartet wird (kein Crash mehr).
- **UI**: Optimiertes Layout für Urlaubs-Saldo und Abwesenheiten-Tabelle.

### v2.8.0
## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/manueloberberger/incode-cli.git
cd incode-cli

# 2. Install & Setup (Automated)
./install.sh
```

## 💡 Usage

Simply run the wrapper script. It automatically manages the virtual environment for you:

```bash
./incode
```

*On the first run, you will be prompted for your Incode credentials. They are stored securely and locally on your machine.*
