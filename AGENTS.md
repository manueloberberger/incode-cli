# AGENTS.md

## Project

Incode CLI is a Python terminal interface for the Austrian Red Cross duty-roster system. It prioritizes fast keyboard navigation, local data privacy, and compatibility with Python 3.9+ on macOS and Linux.

## Commands

```bash
# Application
./incode
./incode bot
./incode bot --debug
./incode --export [FILE]
./incode --import <FILE>

# Development environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Verification
.venv/bin/python3 -m pytest tests/ -v
.venv/bin/python3 -m pytest tests/test_api.py -v
.venv/bin/python3 -m mypy --strict incode.py src/
./test-compatibility.sh
```

Run the smallest relevant test first, then the full test suite and strict mypy check for changes that affect Python code. Run `test-compatibility.sh` when installation, shell, platform, or packaging behavior changes.

## Architecture

- `incode.py` is the application entry point; `./incode` activates the virtual environment and launches it.
- `src/api_async.py` is the asynchronous HTTP client. `src/api.py` is the synchronous facade used by UI code.
- `src/db.py` owns SQLite persistence for credentials, settings, cache, and value-store data.
- `src/parser.py` parses upstream HTML and attendance data.
- `src/models.py` contains domain models such as `Duty`.
- `src/bot.py` contains the Telegram duty-roster bot.
- `src/service.py` manages Linux systemd and macOS launchd services.
- `src/backup.py` owns export/import and path-safety checks.
- `src/updates.py` owns self-update behavior.
- `src/ui/` contains the Rich-based terminal interface.
- Shared business logic belongs in `src/utils.py`, not duplicated across views.

## Project Rules

- Use Rich for user-facing terminal output; do not introduce plain `print()` calls in application UI paths.
- Preserve the async/sync boundary: network concurrency belongs in `api_async.py`; UI callers use the facade in `api.py`.
- Treat credentials and roster data as sensitive local data. Never commit credentials, tokens, databases, exported rosters, or personal contact data.
- Maintain Python 3.9 compatibility and portable macOS/Linux behavior. Avoid GNU-only shell flags in installation scripts.
- Prefer focused functions, explicit exception types, type hints, and strict-mypy-compatible code.
- Add or update tests for every behavior change.

## Versioning and Releases

- Use semantic commit prefixes such as `feat:`, `fix:`, `refactor:`, and `chore:`.
- Every feature or fix requires a version bump.
- Keep `VERSION` in `src/config.py` and the version badge in `README.md` synchronized.
- Update `CHANGELOG.md` and relevant user documentation for release-visible changes.

## Current Baseline

The current release baseline is v2.30.0. Important implemented behavior includes:

- Cancelled duties from API attendance data are hidden from views and statistics.
- `Duty.is_cancelled` is populated by the parser, and `get_next_duty()` skips cancelled duties.
- Training duties are not incorrectly filtered as absences.
- Duty display names prefer meaningful shift names and strip bracket prefixes such as `[FB]`.
- The bot monitors duty-roster changes and stores per-user snapshots in the SQLite value store.
- Cache cleanup, backup path validation, secure temporary files, API error classification, and async cleanup are already implemented.

Before relying on this baseline, confirm behavior against the current code and tests; the code is the source of truth.
