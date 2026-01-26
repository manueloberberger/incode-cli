# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Incode CLI** is a Python-based terminal user interface for the Austrian Red Cross duty roster system ("Incode"). It prioritizes speed, keyboard navigation, and local data privacy.

## Common Commands

```bash
# Run the application
./incode                          # Interactive TUI mode
./incode bot                      # Telegram bot mode (auto-login)
./incode bot --debug              # Bot with verbose logging
./incode --export [FILE]          # Export backup
./incode --import <FILE>          # Import backup

# Development setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run directly with Python
.venv/bin/python3 incode.py

# Testing
.venv/bin/python3 -m pytest tests/ -v
.venv/bin/python3 -m pytest tests/test_api.py -v  # Single test file

# Type checking
.venv/bin/python3 -m mypy --strict incode.py src/

# Compatibility check (bash scripts)
./test-compatibility.sh
```

## Architecture

### Entry Point
- `incode.py`: Main application entry point
- `./incode`: Shell wrapper that activates venv automatically

### Core Modules (`src/`)

| Module | Purpose |
|--------|---------|
| `api.py` | Synchronous facade wrapping async client |
| `api_async.py` | Async HTTP client using aiohttp with parallel fetching |
| `config.py` | Constants, versioning (`VERSION`), credential management |
| `db.py` | SQLite database layer (`incode.db`) |
| `parser.py` | HTML parsing (BeautifulSoup) |
| `models.py` | Data models (e.g., `Duty`) |
| `bot.py` | Telegram bot integration |
| `service.py` | System service installation (Linux/systemd, macOS/launchd) |
| `holidays.py` | Austrian holiday calculation |

### UI Layer (`src/ui/`)
Modular TUI using [Rich](https://github.com/Textualize/rich):
- `components.py`: Shared widgets (interactive menus, date picker)
- `dashboard.py`: Future duties view
- `daily_plan.py`: Single day view
- `staff.py`: Staff directory and colleague search
- `settings.py`: User settings

## Key Architectural Decisions

1. **Async/Sync Bridge**: `api.py` provides sync methods that wrap async operations from `api_async.py`, enabling parallel network requests without async/await in UI code.

2. **UI Library**: All terminal output uses Rich. Never use standard `print()`.

3. **Centralized Logic**: Business logic shared across views belongs in `src/utils.py` (e.g., holiday calculation).

4. **Credential Storage**: Uses SQLite (`incode.db`) for all user data. Never commit credentials.

5. **Caching**: API responses cached locally with ~15 minute TTL.

## Git & Versioning

- **Commits**: Use semantic prefixes (`feat:`, `fix:`, `refactor:`, `chore:`)
- **Version**: Bump `VERSION` in `src/config.py` for releases. **IMPORTANT**: Always update the version badge in `README.md` to match!
- **CI**: GitHub Actions runs tests on Python 3.9, 3.11, 3.12

## Recent Context (2026-01-26)
*State at v2.19.0*

- **Documentation Overhaul Completed**: 
    - All core modules (`service`, `bot`, `db`, `incode`) and key UI views are now fully documented with docstrings.
    - `README.md` now covers Multi-User Support and Telegram Bot setup in detail.
- **Rule Added**: Always sync `VERSION` in `src/config.py` with the badge in `README.md`.
- **Tests**: Full suite (131 tests) passing.
- **Next Steps**: Project is stable. Future work can focus on new features as the technical debt (docs/tests) is resolved.
