<div align="center">

![incode-cli Banner](.github/banner.png)

[![Version](https://img.shields.io/badge/version-2.31.2-blue.svg?style=flat-square)](https://github.com/manueloberberger/incode-cli) ![Python](https://img.shields.io/badge/python-3.9%2B-green?style=flat-square) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**The lightning-fast, keyboard-driven interface for the Red Cross duty roster.**

[Installation](#-installation) • [Features](#-features) • [Usage](#-usage) • [Contributing](#-contributing)

</div>

---

## ✨ Features

- 🚀 **Lightning Fast**: Optimized startup and navigation
- ⌨️ **Keyboard-Driven**: Efficient TUI (Terminal User Interface)
- 👥 **Multi-User Support**: Manage multiple accounts
- 📊 **Duty Roster Management**: View and manage your shifts
- 📇 **Staff Directory**: Quick access to contact information
- 📈 **Statistics & Analytics**: Track your work hours
- 🔄 **Smart Auto-Updates**: Self-updating app & background services
- 💾 **Backup & Restore**: Export/Import your data seamlessly
- 🔒 **Secure & Local**: Credentials stored locally on your machine

---

## 🚀 Installation

### Quick Install (One-Liner)

```bash
curl -sSL https://raw.githubusercontent.com/manueloberberger/incode-cli/main/quick-install.sh | bash
```

This automatically clones the repository to `~/.local/share/incode-cli` and installs everything.

### Manual Install

```bash
# 1. Clone the repository
git clone https://github.com/manueloberberger/incode-cli.git
cd incode-cli

# 2. Run the installer
./install.sh
```

The installer will:
- ✅ Check Python version (3.9+ required)
- ✅ Create a virtual environment
- ✅ Install dependencies
- ✅ Create a global `incode` command in `~/.local/bin`

> **Note**: Make sure `~/.local/bin` is in your PATH. Add this to your `~/.zshrc` or `~/.bashrc`:
> ```bash
> export PATH="$HOME/.local/bin:$PATH"
> ```

### Uninstall

```bash
./uninstall.sh
```

This removes the symlink, virtual environment, and optionally your credentials.

---


### Usage

Run from anywhere:

```bash
incode
```

Or use the local wrapper:

```bash
./incode
```

*On the first run, you will be prompted for your Incode credentials. They are stored securely and locally on your machine.*

### 👥 Multi-User Support

Incode CLI supports multiple user accounts (personas) simultaneously. This is useful for:
- Managing different credentials for different organizations
- Switching between user and bot accounts

**Commands:**
- **Switch User**: Select "Benutzer wechseln" in the main menu.
- **Add User**: Select "Neuen Benutzer hinzufügen" in the login screen.
- **CLI Login**: Start directly as a specific user:
  ```bash
  ./incode --user "Max Mustermann"
  ```
- **Interactive Selection**: Force the selection menu on startup:
  ```bash
  ./incode --select
  ```

### 🤖 Telegram Bot

The built-in Telegram Bot allows you to query your duty roster from your smartphone.

**Setup:**
1. Run `./incode bot` interactively.
2. Enter your Bot Token (from @BotFather).
3. Enter your Telegram User ID (from @userinfobot).
4. The bot is now configured!

**Running the Bot:**

- **Interactive Mode**:
  ```bash
  ./incode bot
  ```
  *Auto-logs in with the last active user.*

- **Specific User**:
  ```bash
  ./incode bot --user "Max Mustermann"
  ```
  *Starts the bot for a specific user profile.*

- **Background Service**:
  To keep the bot running 24/7, install it as a system service:
  ```bash
  ./incode install-service --user "Max Mustermann"
  ```
  *Supports systemd (Linux) and launchd (macOS).*

### Roster filters and statistics

In **Mein Dienstplan**, press **F** to choose completed duties, planned/ongoing
duties, the current month/year, or any month present in the loaded data. **R**
refreshes from the server. PDF and calendar exports use the displayed filter.

Monthly hours separate completed from planned/ongoing shifts. Hours are attributed
to the start month of each shift. Statistics summarize the loaded roster rather
than claiming a complete year. The compact summary shows service categories (including KTWB and BKTW) and stations;
individual shift labels stay in the roster instead of creating extra statistics
categories. Regular duties at Feistritz/Drau count as SEW based on the station. Explicit
training, ambulance and special-duty labels retain their own compact categories.
Elsewhere, explicit service labels take priority over the vehicle type; Villach
is never classified as SEW from its location alone. A missing vehicle remains
unknown when neither label nor station identifies the service, and all hours
are still counted.

### Reliability and exports

Network requests have explicit time limits. Failed or incomplete responses produce
a recoverable error rather than an empty roster. Views offer **R** to retry;
roster and daily-plan views identify cached data. The live monitor fetches fresh
data, keeps the last valid display after a failed request and reports actual
Telegram delivery results.

The duty-change monitor detects crew, station, time, vehicle and comment changes.
Its upgraded snapshot is initialized silently on first use. Requests from bot
workers sharing a client are serialized.

Duty identifiers supplied by the server are retained through parsing, merging,
caching and exports. Calendar UIDs use these identifiers and the account scope;
without a server identifier a composite fallback is used, so changing its time,
vehicle or location can still create a new calendar identity. Calendar imports
remain dependent on the receiving app; an exported file is not a calendar sync.
Local calendar times explicitly use Europe/Vienna, and export timestamps use UTC.

Self-updates require a clean working tree, including untracked files. If you have
local changes, save them outside the checkout or commit them before retrying.
The updater leaves those changes untouched and does not automatically stash them.

---

## 🧪 Testing

To verify cross-platform compatibility on your system:

```bash
./test-compatibility.sh
```

This script checks:
- Bash syntax of installation scripts
- Required commands (python3, git, curl, etc.)
- Platform detection
- Python version
- PATH configuration

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---



