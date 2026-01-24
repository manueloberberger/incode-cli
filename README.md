# Incode CLI 🚑

![Version](https://img.shields.io/badge/version-2.7.1-blue?style=flat-square) ![Python](https://img.shields.io/badge/python-3.9%2B-green?style=flat-square)

**The lightning-fast, keyboard-driven interface for the Red Cross duty roster.**

---


## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/manueloberberger/incode-cli.git
cd incode-cli

# 2. Install & Setup (Automated)
./install.sh
```

## ✨ Features

- **⚡️ Lightning Fast**: Instant startup and navigation thanks to local SQLite caching.
- **👥 Multi-User**: Seamlessly manage and switch between multiple accounts.
- **🔍 Smart Search**: Fuzzy search for staff, colleagues, and projects across your organization.
- **📅 Interactive Roster**: View your duties, absences, and team schedules in a beautiful TUI.
- **📺 Live Monitor**: Real-time dashboard for vehicle status and crew info.
- **🤖 Telegram Bot**: Integrated bot for easy PDF export and mobile access.

## 💡 Usage

Simply run the wrapper script. It automatically manages the virtual environment for you:

```bash
./incode
```

*On the first run, you will be prompted for your Incode credentials. They are stored locally in a portable **SQLite database** (`incode.db`) within the project folder.*
