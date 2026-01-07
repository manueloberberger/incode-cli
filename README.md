# incode-cli 🚑

A high-performance CLI tool for Red Cross staff to manage rosters, absences, and event duties. Designed for speed, reliability, and advanced analytical insights into work schedules.

## 🚀 Features

- **Personal Roster:** Real-time access to your upcoming shifts with detailed crew information.
- **Advanced Absence Management:** Automated tracking of vacations, public holidays, and custom absence wishes.
- **Event & Ambulanz Services:** Dedicated overview of medical services at events with open slot tracking.
- **Live Monitor:** Continuous background tracking of current-day operations with automated Telegram notifications on changes.
- **Smart Statistics:** Monthly hour analysis and duty distribution by vehicle type/location.
- **Multi-Format Export:** High-quality PDF generation and iCal (ICS) calendar sync.
- **Telegram Integration:** Built-in bot logic to receive schedules and notifications directly on your phone.
- **Auto-Update:** Automatically detects new versions, performs `git pull` and updates dependencies via `pip`.

---

## 🛠 Technical Architecture

The application is built using a modular Python-based architecture:

- **`incode.py`:** The main entry point handling CLI arguments and the interactive UI loop.
- **`src/api.py`:** Core logic for interacting with the StaffPortal. Uses `requests` with a custom `TimeoutHTTPAdapter` and `urllib3` retry strategies for maximum reliability.
- **`src/ui.py`:** Rich-based TUI (Terminal User Interface) components for interactive menus, tables, and live monitors.
- **`src/bot.py`:** Asynchronous Telegram bot implementation for notifications and document delivery.
- **`src/pdf.py` & `src/ical.py`:** Specialized modules for generating formatted documents and calendar files.
- **`src/utils.py`:** Shared utilities for screen management, input handling, and automatic update checks.

---

## 🌴 Advanced Absence Logic (Technical Deep-Dive)

The most complex part of the tool is the absence tracking logic, which reconstructs a logical timeline from disparate API data points:

### 1. Multi-Source Aggregation
Data is pulled from three distinct endpoints:
- `absence/data/load.json`: Fixed approved roster absences.
- `absence/data/loadWishes.json`: Pending and approved absence wishes.
- `duties/data/load.json`: Regular duty plan (used as a fallback for specific absence markers).

### 2. Intelligent Labeling & Priority
The tool applies a priority-based daily mapping strategy:
- **Prioritization:** Specific markers like `Urlaub`, `Krank`, or `Abwesend` always overwrite generic markers like `Freies Wochenende`.
- **Public Holidays:** Automatically calculates Austrian public holidays using the **Gauss Easter Algorithm**.
- **Holiday Context:** 
    - Public holidays falling on Mon-Sat are labeled as **"Geplante Sonderabwesenheit"**.
    - Public holidays falling on a **Sunday** are labeled as **"Abwesend"**.
- **Special Rules (Kärnten):** Includes the 10.10. (Carinthian Referendum Day) and excludes Good Friday (Karfreitag) from holiday status (treated as vacation).

### 3. Weekend Reconstruction
To provide a complete calendar view, the tool synthetically generates weekend markers:
- **Pre-Vacation Sunday:** If a free block (Vacation/Holiday) starts on a Monday, the preceding Sunday is labeled as **"Freies Wochenende"**.
- **Post-Vacation Sunday:** If a free block ends on a Saturday, the following Sunday is labeled as **"Abwesend"**.

---

## 🔐 Security & Configuration

Credentials and session data are handled securely:
- **`.credentials.json`:** Stores username, encrypted-ish password (handled by the system keyring where possible), and org-unit GUIDs. File permissions are automatically set to `600` (read/write by owner only).
- **`.incode_cache.json`:** Encrypted local cache for API responses to enable offline mode and reduce server load.
- **Headers:** Automatically extracts `x-incode-*` security tokens from JavaScript assets during login to mimic an authorized browser session.

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/manueloberberger/incode-cli.git
cd incode-cli

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the application
python3 incode.py
```

## 🤖 Bot Setup

To enable Telegram notifications:
1. Create a bot via [@BotFather](https://t.me/botfather).
2. Obtain your Chat ID via [@userinfobot](https://t.me/userinfobot).
3. Select "Telegram Bot" in the main menu to configure the token and ID.

---

*Note: This tool is an independent implementation and not an official product of the Red Cross.*
