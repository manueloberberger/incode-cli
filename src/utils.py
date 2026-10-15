"""
Utility functions for incode-cli.
This module provides common utilities and re-exports from submodules for backwards compatibility.
"""
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar, Union, Dict, List, Sequence, Tuple
from dataclasses import asdict
import hashlib
import json
import re
from src.models import Duty
from functools import wraps
import logging

from requests import RequestException
from requests.adapters import HTTPAdapter

from src.config import DEFAULT_TIMEOUT

# Re-exports for backwards compatibility
from src.input import (
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,
    KEY_UP_ALT, KEY_DOWN_ALT, KEY_LEFT_ALT, KEY_RIGHT_ALT,
    KEY_ENTER, KEY_ESC, KEY_BACKSPACE,
    clear_screen, flush_input, get_key,
    wait_for_return, prompt_yes_no, centered_input, unicode_len
)
from src.updates import check_for_updates, update_app
from src.holidays import get_holidays

# Explicit exports for mypy --strict
__all__ = [
    # Key constants
    "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT",
    "KEY_UP_ALT", "KEY_DOWN_ALT", "KEY_LEFT_ALT", "KEY_RIGHT_ALT",
    "KEY_ENTER", "KEY_ESC", "KEY_BACKSPACE",
    # Input functions
    "clear_screen", "flush_input", "get_key",
    "wait_for_return", "prompt_yes_no", "centered_input", "unicode_len",
    # Update functions
    "check_for_updates", "update_app",
    # Holiday functions
    "get_holidays",
    # Datetime functions
    "parse_iso_datetime",
    # Classes
    "TimeoutHTTPAdapter",
    # Decorators
    "handle_api_errors",
]
T = TypeVar("T")

logger = logging.getLogger(__name__)


def parse_iso_datetime(value: Optional[Union[str, datetime]]) -> Optional[datetime]:
    """
    Parse an ISO datetime string without timezone adjustment.

    Handles both full ISO format (with 'T') and space-separated format.
    Safely handles None, empty strings, and already-parsed datetime objects.

    Args:
        value: ISO format datetime string, datetime object, or None.

    Returns:
        Datetime object, or None if parsing fails or input is empty.

    Examples:
        >>> parse_iso_datetime('2024-01-15T08:00:00')
        datetime(2024, 1, 15, 8, 0, 0)
        >>> parse_iso_datetime('2024-01-15 08:00:00')
        datetime(2024, 1, 15, 8, 0, 0)
        >>> parse_iso_datetime(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        s = value[:19]
        if 'T' in s:
            return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
        else:
            return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, IndexError):
        return None


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def handle_api_errors(default_return: Any = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to handle API errors gracefully.
    Logs error and returns default_return.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except RequestException as e:
                logger.error(f"Netzwerk-Fehler in {func.__name__}: {e}")
            except Exception as e:
                logger.error(f"Unerwarteter Fehler in {func.__name__}: {e}")
            return default_return  # type: ignore
        return wrapper
    return decorator



def duty_identity(duty: Union[Duty, Dict[str, Any]]) -> str:
    """Stable upstream identity; conservative composite fallback for legacy data."""
    data = asdict(duty) if isinstance(duty, Duty) else duty
    def identity_value(key: str) -> str:
        value = data.get(key)
        parsed = parse_iso_datetime(value) if key in ("begin", "end") else None
        return parsed.isoformat() if parsed is not None else str(value or "")

    source_id = data.get("source_id")
    if source_id:
        values = ["id", data.get("source_scope", ""), str(source_id)]
    else:
        values = ["legacy", data.get("source_scope", "")] + [
            identity_value(key) for key in
            ("begin", "end", "vehicle", "location", "duty_type")
        ]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False).encode("utf-8")).hexdigest()


def merge_duties(primary: Sequence[Duty], archive: Sequence[Duty]) -> List[Duty]:
    """Keep concurrent duties, prefer current data, enrich missing archive fields."""
    merged = {duty_identity(d): d for d in primary}
    for archived in archive:
        key = duty_identity(archived)
        current = merged.get(key)
        if current is None:
            merged[key] = archived
        else:
            for field in ("location", "vehicle", "duty_type", "crew", "comment"):
                if not getattr(current, field) and getattr(archived, field):
                    setattr(current, field, getattr(archived, field))
    return sorted(merged.values(), key=lambda d: (d.begin, d.end, d.vehicle or ""))


def duty_fingerprint(duty: Dict[str, Any]) -> str:
    """Compare meaningful details, ignoring crew ordering and response ordering."""
    data = {key: duty.get(key) for key in
            ("begin", "end", "vehicle", "location", "duty_type", "comment", "is_cancelled")}
    crew = duty.get("crew") or []
    data["crew"] = sorted(crew.items()) if isinstance(crew, dict) else sorted(crew)
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str,
                                    ensure_ascii=False).encode("utf-8")).hexdigest()


def vehicle_category(vehicle: Optional[str]) -> str:
    """Match full vehicle tokens so KTWB/BKTW cannot accidentally become KTW."""
    text = (vehicle or "").strip().upper()
    match = re.search(r"(?<![A-Z])(RTWA|RTW|KTWB|BKTW|KTW|BTW|NEF|VEF)(?![A-Z])", text)
    return match.group(1) if match else (text or "Ohne Fahrzeug")


def duty_category(duty: Duty) -> str:
    """Classify service labels first, then the confirmed Feistritz location rule."""
    label = duty.duty_type or ""
    if re.search(r"fortbildung|ausbildung|schulung|seminar|lehrgang", label, re.IGNORECASE):
        return "Fortbildung"
    for pattern, category in ((r"ambulanz", "Ambulanzdienst"),
                              (r"fernfahrt", "Fernfahrt"),
                              (r"sonstiger dienst", "Sonstiges")):
        if re.search(pattern, label, re.IGNORECASE):
            return category
    location = " ".join((duty.location or "").casefold().split())
    if re.fullmatch(r"(?:ost )?feistritz(?:\s*/\s*drau| an der drau)?", location):
        return "SEW"
    explicit = re.search(r"(?<![A-Z])(SEW|RTWA|RTW|KTWB|BKTW|KTW|BTW|NEF|VEF)(?![A-Z])", label.upper())
    if explicit:
        return explicit.group(1)
    # No location-based SEW inference for Villach or other stations.
    return vehicle_category(duty.vehicle)


def filter_duties(duties: Sequence[Duty], period: str, now: datetime) -> List[Duty]:
    """Filter all representations consistently; include ongoing shifts as planned."""
    return [d for d in duties if not d.is_cancelled and
            (not period.startswith("month:") or d.begin.strftime("%Y-%m") == period[6:]) and
            (period != "completed" or d.end <= now) and
            (period != "planned" or d.end > now) and
            (period != "month" or (d.begin.year, d.begin.month) == (now.year, now.month)) and
            (period != "year" or d.begin.year == now.year)]


def duty_hours(duties: Sequence[Duty], now: datetime) -> Dict[str, Tuple[float, float]]:
    """Monthly completed and planned hours, attributed to the shift's start month."""
    result: Dict[str, Tuple[float, float]] = {}
    for duty in duties:
        if duty.is_cancelled:
            continue
        month = duty.begin.strftime("%Y-%m")
        completed, planned = result.get(month, (0.0, 0.0))
        if duty.end <= now:
            completed += duty.duration_hours
        else:
            planned += duty.duration_hours
        result[month] = completed, planned
    return result
