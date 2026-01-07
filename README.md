# 🚑 Incode CLI v1.8

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-BETA-orange.svg)]()
[![License](https://img.shields.io/badge/License-Internal-red.svg)]()

**Incode CLI** is a high-performance terminal interface for the Red Cross StaffPortal (Incode). It transforms a legacy web experience into a modern, automated, and feature-rich developer-grade environment.

---

## ⚡ Core Engines

### 🔍 The "Vacuum" GUID Discovery
Traditional scrapers fail when Orgunits or Projects are nested or hidden in JavaScript variables. Incode CLI implements a **GUID Vacuum Engine** that recursively scans DOM trees and JS blocks for 160-bit hex patterns.
- Automatically identifies all accessible `orgUnitDataGuids`.
- Injects discovered IDs into API requests to bypass front-end filtering.
- Maps IDs to human-readable names via a sibling-traversal heuristic.

### 🎭 Hybrid Extraction Layer (HEL)
The portal's JSON endpoints often provide incomplete datasets (missing event names or empty slots). HEL handles this by:
1. **Parallel Execution:** Fetching raw JSON for data structure AND raw HTML for metadata.
2. **DOM Reconstruction:** Rebuilding event objects by matching JSON `parentDataGuid` with HTML `data-` attributes.
3. **Regex Overlays:** Using non-deterministic regex patterns to extract "Bedarf" (open slots) when standard parsers fail.

### 📊 Statistical Intelligence
Beyond simple display, the CLI computes:
- **Net-Vacation Logic:** Calculates real holiday usage by applying the **Gauss Easter Algorithm** to exclude weekends and public holidays dynamically.
- **Duty Distribution:** Cluster analysis of vehicle types and deployment locations.

---

## 🚀 Features at a Glance

| Feature | Description | Technical Core |
| :--- | :--- | :--- |
| **Mein Dienstplan** | Interactive table of future duties. | Monthly chunking, month-over-month stats. |
| **Events / Ambulanzen** | Detailed overview of upcoming events. | card-based HTML parsing, GUID-mapping. |
| **Live Monitor** | 24/7 terminal dashboard. | Differential state-tracking, Telegram webhooks. |
| **Staff Search** | Complete directory lookup. | Multi-field search (PNR, Skill, Occupation). |
| **PDF/iCal Export** | Export your life to your devices. | ReportLab vector gen, icalendar RFC5545. |

---

## 🛠 Tech Stack

- **Language:** Python 3.10+
- **Terminal UI:** [Rich](https://github.com/Textualize/rich) (Live-layouts, Tables, Panels)
- **Networking:** [Requests](https://requests.readthedocs.io/) with custom `HTTPAdapter` for aggressive retries.
- **Parsing:** [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) with `lxml`.
- **Bot Layer:** [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (AsyncIO).

---

## 📦 Quick Start

```bash
# Clone the repository
git clone https://github.com/manueloberberger/incode-cli.git && cd incode-cli

# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the CLI
python3 incode.py
```

## 🤖 Bot Deployment
To run the Telegram Bot as a background process:
```bash
python3 incode.py bot &
```

---

## 🛡 Security & Privacy
- **Stateless by Default:** Sensitive cookies are kept in memory or temporary local cache only.
- **Local Credentials:** `.credentials.json` is automatically chmodded to `600` and excluded from git tracking.
- **No Third-Party Analytics:** Your data stays between you and the Red Cross server.

---
*Developed for professionals. Built for speed.*