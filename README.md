# Incode CLI 🚑

![Version](https://img.shields.io/badge/version-1.9.0-blue) ![Python](https://img.shields.io/badge/python-3.9%2B-green) ![Architecture](https://img.shields.io/badge/architecture-modular-orange)

**Incode CLI** is a high-performance, reverse-engineered Terminal User Interface (TUI) for the Red Cross Austria's duty roster system ("Incode" / "StaffPortal").

It serves as a drop-in replacement for the legacy web interface, providing power users with speed, keyboard-centric navigation, and advanced data aggregation features that are technically impossible in the standard web client.

```text
   ___ _  _  ___  ___  ___  ___       ___ _    ___   
  |_ _| \| |/ __|/ _ \|   \| __|     / __| |  |_ _|  
   | || .  | (__| (_) | |) | _|     | (__| |__ | |   
  |___|_|\_|\___|\___/|___/|___|     \___|____|___|  
```

---

## 🏗 Technical Architecture

The application is built on **Python 3** and utilizes a modular architecture designed for resilience and performance. It operates by emulating a full web browser session to communicate with the undocumented backend API.

### 1. Core API & Reverse Engineering (`src/api.py`)
Since Incode does not expose a public API, the CLI acts as a headless client.

*   **Header Spoofing & Session Management:**
    The backend requires dynamic, rotating security headers (`x-incode-*`). The CLI authenticates via `/login.php`, captures the `PHPSESSID`, and uses Regular Expressions to extract these dynamic tokens from the embedded JavaScript of the landing page to sign subsequent requests.
*   **Recursive GUID Discovery:**
    Data in Incode is siloed by "Organizational Units" (districts/departments), identified by GUIDs.
    The CLI recursively scrapes these GUIDs (`StaffPortal/dispo.php`, `projects.php`) to build a complete map of the user's access rights. This enables **cross-departmental queries**, allowing the user to find staff members or shifts in guest districts that are normally hidden.
*   **Caching Layer:**
    To ensure instantaneous UI rendering, API responses are serialized and stored in a local JSON cache (`.incode_cache.json`) with a strict TTL (Time-To-Live) of 15 minutes.

### 2. Algorithmic Data Processing

#### The "Sandwich" Absence Logic
The web interface often mislabels days within a vacation block as generic "Free Weekends," causing payroll confusion.
*   **Heuristic:** The CLI analyzes the timeline. If a Sunday is sandwiched between a vacation Friday/Saturday and a vacation Monday, the algorithm reclassifies the Sunday as a "Vacation Day" (part of the continuous block).
*   **Holiday Engine:** A custom engine calculates Austrian holidays (including variable Easter dates) to correctly prioritize "Holiday" status over "Vacation" or "Free" statuses.

#### Weighted Staff Deduplication
Staff records are often fragmented across multiple organizational units (e.g., a "Skeleton" record in a guest district vs. a "Full" record in the home district).
*   **Merging Strategy:** The `search_staff_contact` function aggregates records from *all* discovered GUIDs.
*   **Scoring System:** It applies a weighted scoring algorithm to duplicates (matched by Name or PNR).
    *   `+10` points for a phone number.
    *   `+10` points for an email address.
    *   `+5` points for assigned roles.
    The system automatically merges these records, presenting the user with a single, "Golden Record" containing the most complete dataset available.

### 3. TUI & Event Loop (`src/ui.py`)
The interface is built using the **Rich** library for rendering.
*   **Responsive Layout engine:** Tables and Panels utilize `expand=False` and `Align.center` strategies to render cleanly on everything from small laptop screens to ultrawide monitors.
*   **Custom Input Handling:** A cross-platform input wrapper (`src/utils.py`) handles `msvcrt` (Windows) and `termios/tty` (Linux/macOS) to provide a lag-free, non-blocking event loop for keyboard navigation.

### 4. Robust Auto-Update (`src/utils.py`)
The CLI maintains its own lifecycle.
*   **Atomic Updates:**
    1.  Checks for upstream changes (`git fetch`).
    2.  **Stashes** any local modifications (`git stash`) to prevent merge conflicts.
    3.  Pulls the latest code (`git pull`).
    4.  Silently updates dependencies (`pip install`).
    5.  Restores local modifications (`git stash pop`).

---

## ⚡ Features & Capabilities

*   **Global Staff Directory:** Search across all organizational units with phone number formatting (+43...) and deep linking of skills/groups.
*   **Live Roster Monitor:** Real-time polling of the daily plan (`/StaffPortal/plan/data/loadPlan.json`). Ideal for station monitors.
*   **Telegram Bridge:** An asynchronous bot (`src/bot.py`) that can push PDF rosters or live alerts directly to the user's smartphone.
*   **PDF & iCal Generation:** Client-side generation of roster files using `reportlab` (PDF) and `icalendar` (ICS) for offline usage and calendar integration.

---

## 📦 Installation

### Prerequisites
*   Python 3.9+
*   Git

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/incode-cli.git
cd incode-cli

# 2. Create Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Run
python3 incode.py
```

*Note: Credentials are requested on the first run and stored securely (`chmod 600`) in `.credentials.json`. They are never transmitted anywhere except the official Incode servers.*

---

## 🔒 Security & Privacy

*   **Zero-Knowledge:** The CLI does not track usage or send telemetry.
*   **Local Storage:** Credentials and Cache are stored strictly locally and added to `.gitignore`.
*   **Direct Communication:** All traffic goes directly from your client to `https://dienstplan.k.roteskreuz.at`. There is no middleman server.

---

## ⚖️ Disclaimer

This software is an independent, open-source project and is **not affiliated with, endorsed by, or supported by the Austrian Red Cross or Incode GmbH**. Use it at your own risk.

---

*Engineered by Manuel Oberberger*