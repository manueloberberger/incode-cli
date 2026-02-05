# Changelog

All notable changes to incode-cli will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.26.0] - 2026-02-05

### Added
- New test file `test_updates.py` with 10 tests for update checking and application
- New test file `test_api_async.py` with 16 async tests for the API client
- Extended `test_ui.py` with UI module export validation tests
- Total test count increased from 186 to 221

## [2.25.0] - 2026-02-05

### Changed
- Wrapped blocking `get_key()` call in `asyncio.to_thread()` to prevent async event loop blocking
- Improved exception handling: use `LoginError` instead of generic `Exception` in bot.py
- `api.py`: catch specific exceptions (`KeyError`, `ValueError`, `TypeError`) before generic fallback

## [2.24.0] - 2026-02-05

### Added
- Periodic cache cleanup in Bot mode (every 15 minutes) to prevent unbounded growth
- Path validation in `backup.py` to prevent access to system directories

### Security
- Replaced predictable `/tmp/` paths with `tempfile.mkstemp()` in `service.py`
- Secure file permissions: `0o600` for service files, `0o700` for scripts

## [2.23.0] - 2026-02-01

### Added
- `/help` command in Telegram bot with full command reference
- Database indexes on `cache.timestamp` and `users.username` for faster queries
- Automatic cache cleanup on application startup
- Comprehensive documentation for exception classes
- Detailed Computus algorithm documentation in `holidays.py`
- Regex pattern documentation in `api_async.py`
- 11 new tests for bot help, corrupted backups, and service restart

### Changed
- Replaced runtime `assert` statements with proper `RuntimeError` exceptions in `api_async.py`
- Improved exception handling: specific exceptions instead of broad `except Exception`
- Dependencies now use version ranges for better security update support
- Upgraded `python-telegram-bot` to >=21.7
- Added `types-aiohttp` for complete type checking
- Optimized string concatenation in `parser.py` using `join()`

### Fixed
- Silent error handling in `pdf.py` now logs skipped entries
- Login error message now includes troubleshooting suggestions

## [2.22.0] - 2026-01-27

### Added
- `parse_iso_datetime()` utility function for consistent datetime parsing
- Staff caching with TTL (~15 min) for improved performance
- PDF exception logging for better error diagnostics
- Pre-compiled vehicle regex pattern (`VEHICLE_PATTERN`)
- Specific error handling for backup operations (PermissionError, OSError)

### Changed
- Event loading now uses O(1) dictionary lookup instead of O(n) nested loops
- Refactored datetime parsing across 6 files to use central utility

### Fixed
- Removed unused variables and parameters (dead code cleanup)
- mypy --strict compatibility improvements

## [2.19.0] - 2026-01-26

### Added
- Complete internal documentation:
  - Docstrings for `incode.py` (Entry Point)
  - Docstrings for `src/db.py` (Database Layer)
  - Docstrings for `src/ui/settings.py` & `src/ui/staff.py`
  - Docstrings for `src/service.py` & `src/bot.py`
- New `README.md` sections for Multi-User & Telegram Bot usage
- Explicit version sync rule in `CLAUDE.md`

## [2.18.0] - 2026-01-26

(Skipped version, see 2.19.0)

## [2.16.5] - 2026-01-25

### Fixed
- Fixed vacation calculation: Holidays (24.12, 31.12, etc.) override vacation (count as 'Sonderabwesenheit')
- Removed 'Karfreitag' from holidays list so it correctly counts as 'Urlaub'

## [2.16.4] - 2026-01-25

### Fixed
- Fixed logic issue where vacation on holidays was incorrectly labeled as "Geplante Sonderabwesenheit"

## [2.16.3] - 2026-01-25

### Fixed
- Fixed all linter warnings (unused imports, variables)
- Code cleanup and optimizations

## [2.16.2] - 2026-01-25

### Added
- Comprehensive docstrings across all modules (83 → 169)
- New test files: `test_db.py` (18 tests), `test_holidays.py` (22 tests)
- Centralized logging setup in `src/config.py` (logs to `incode.log`)
- Dataclass support (`Duty`) for PDF and iCal exports
- Total test count increased from 10 to 50

### Changed
- Split `utils.py` into modular components:
  - `input.py` - Keyboard/terminal I/O handling
  - `updates.py` - Update checking and app update logic
  - `holidays.py` - Austrian holiday calculations
- Enhanced GitHub Actions CI with Python 3.9/3.11/3.12 matrix
- Improved `mypy --strict` compliance

### Fixed
- Removed duplicate imports in `incode.py`

## [2.16.1] - 2026-01-24

### Changed
- Improved List View UI
- Fixed type errors

## [2.16.0] - 2026-01-23

### Added
- Scrollable daily plan list view
- Shared cache cleanup functionality

### Fixed
- Various bug fixes

## [2.15.0] - 2026-01-22

### Added
- Automatic service restart on update

## [2.14.0] - 2026-01-20

### Changed
- Optimized Git-based installation with cross-platform support
- Added testing section to README

## [2.13.1] - 2026-01-19

### Fixed
- Added missing Optional import in settings.py

## [2.13.0] - 2026-01-18

### Added
- Enhanced local settings
- State fixes

## [2.12.1] - 2026-01-17

### Added
- Uninstall script
- Auto-cleanup temp files

## [2.12.0] - 2026-01-16

### Added
- Auto-generate installation script for non-root users

## [2.11.6] - 2026-01-15

### Changed
- Cleaner service status messages (remove systemctl noise)

## [2.11.5] - 2026-01-14

### Fixed
- Center service status output for better UX

## [2.11.4] - 2026-01-13

### Added
- Smart uninstall - auto-select if only 1 service installed

## [2.11.3] - 2026-01-12

### Fixed
- Mypy type errors in service.py

## [2.11.2] - 2026-01-11

### Changed
- Unified bot menu (interactive + service management)

## [2.11.1] - 2026-01-10

### Changed
- Hide uninstall option when no services exist
- Dynamic service menu with disabled uninstall state

## [2.11.0] - 2026-01-09

### Added
- Cross-platform service installer (Linux/macOS + menu integration)

## [2.0.0] - 2025-12-XX

### Added
- Multi-user support (manage multiple accounts)
- Login selection menu
- User switching and logout functionality

### Changed
- Migrated `.credentials.json` to support list of users
- Improved startup flow (Banner → Updates → Login)
