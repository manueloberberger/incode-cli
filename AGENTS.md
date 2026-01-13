# Repository Guidelines & Agent Context

## Project Overview
**Incode CLI** is a Python-based command-line interface for the Austrian Red Cross duty roster system ("Incode"). It prioritizes speed, keyboard navigation, and local data privacy.

## Project Structure
- **Entry Point:** `incode.py` (wrapped by `./incode` shell script which handles venv).
- **Core Logic (`src/`):**
  - `api.py`: Handles all HTTP requests, session management, and parsing. **Note:** Uses `ThreadPoolExecutor` for batch fetching.
  - `ui.py`: Renders the TUI using the `rich` library. Focus on interactive menus and tables.
  - `utils.py`: Shared utilities (keys, OS detection) and **centralized business logic** (e.g., `get_holidays`).
  - `bot.py`: Telegram bot integration.
  - `config.py`: Constants, versioning, and credential management.

## Key Architectural Decisions
1.  **Centralization:** Business logic that applies to multiple views (like Holiday calculation) belongs in `src/utils.py`, not duplicated in UI/API layers.
2.  **UI Library:** Exclusively use [Rich](https://github.com/Textualize/rich) for all terminal output. Do not use standard `print()`.
3.  **Performance:** 
    - Network calls affecting lists (like Staff Search) should be parallelized using `ThreadPoolExecutor`.
    - Data should be cached locally in `.incode_cache.json` where appropriate (TTL ~15m).
4.  **Security:** `.credentials.json` must **never** be committed. It is strictly local.

## Development & Testing
- **Environment:** `python3 -m venv .venv && source .venv/bin/activate`
- **Install:** `pip install -r requirements.txt`
- **Run:** `./incode` (Interactive) or `./incode bot --debug` (Bot mode)
- **Testing:** Currently manual. Verify critical flows: Login -> View Plan -> Staff Search -> Exit.

## Git & Versioning
- **Commits:** Use semantic prefixes (`feat:`, `fix:`, `refactor:`, `chore:`).
- **Versioning:** Bump `VERSION` in `src/config.py` for releases.
