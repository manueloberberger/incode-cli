# Incode CLI 🚑

![Version](https://img.shields.io/badge/version-1.9.0-blue?style=flat-square) ![Python](https://img.shields.io/badge/python-3.9%2B-green?style=flat-square) ![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square)

**The lightning-fast, keyboard-driven interface for the Red Cross duty roster.**
Stop clicking through slow web calendars. Start managing your duties like a pro.

```text
   ___ _  _  ___  ___  ___  ___       ___ _    ___   
  |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  
   | || .  | (__| (_) | |) | _|     | (__| |__ | |   
  |___|_|\_|\___|\___/|___/|___|     \___|____|___|  
```

---

## ⚡ Why Incode CLI?

| Feature | 🕸️ Standard Web Portal | 🚀 Incode CLI |
| :--- | :--- | :--- |
| **Speed** | Slow page loads | **Instant** (Local Caching) |
| **Search** | Limited to own district | **Global** (Cross-District Search) |
| **Overview** | Cluttered Calendar | **Clean Lists & Analytics** |
| **Privacy** | - | **Zero-Knowledge** (Local Data only) |

---

## 🔥 Key Features

### 📅 **Roster Management**
*   **Smart Lists:** See all upcoming duties in a clean, sorted list.
*   **Analytics:** Automatic calculation of monthly hours and duty types (RTW vs. KTW).
*   **Team Radar:** Find out when you are working with your favorite colleagues.

### 👥 **Advanced Staff Directory**
*   **Global Search:** Find colleagues even if they are in guest districts.
*   **Deep Details:** View qualifications, group memberships, and current vacation/time-off balances.
*   **Auto-Merge:** Intelligently combines duplicate records to give you the most complete profile (Phone, Email, Roles).

### 🏥 **Live Station Monitor**
*   **Real-time Dashboard:** See exactly who is on duty *right now*.
*   **Auto-Refresh:** Keeps the display updated automatically. Perfect for station screens.

### 🛠 **Power Tools**
*   **PDF & iCal Export:** Generate printable rosters or sync with your phone calendar.
*   **Telegram Integration:** Push rosters directly to your smartphone with one keystroke.
*   **Smart Absences:** Correctly calculates "net" vacation days, fixing the confusing display of the web interface.

---

## 🚀 Getting Started

### Installation

```bash
# 1. Clone & Setup
git clone https://github.com/manueloberberger/incode-cli.git
cd incode-cli

# 2. Install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Make executable (optional but recommended)
chmod +x incode
```

### Usage

Simply run the wrapper script. It handles the virtual environment for you:

```bash
./incode
```

*On the first run, you will be asked for your Incode credentials. They are stored securely (`chmod 600`) on your machine.*

---

## 🏗 Under the Hood

<details>
<summary><strong>Click to expand Technical Architecture</strong></summary>

### Core API & Security
*   **Reverse Engineering:** Emulates a full browser session to communicate with the undocumented backend.
*   **Header Spoofing:** Dynamically extracts security tokens (`x-incode-*`) from the frontend JavaScript.
*   **Recursive Discovery:** Scrapes GUIDs to map all accessible organizational units.

### Algorithms
*   **Sandwich Logic:** Detects if a Sunday is part of a vacation block or a free weekend.
*   **Deduplication:** Uses a weighted scoring system to merge staff records from different sources into a "Golden Record".

### Stack
*   **Python 3.9+**
*   **Rich:** For the responsive TUI.
*   **ReportLab:** For pixel-perfect PDF generation.
</details>

---

**Disclaimer**: This is an independent open-source project and not affiliated with the Red Cross or Incode GmbH.