"""
Utility functions for incode-cli.
This module provides common utilities and re-exports from submodules for backwards compatibility.
"""
from typing import Any, Callable, TypeVar
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
    # Classes
    "TimeoutHTTPAdapter",
    # Decorators
    "handle_api_errors",
]
T = TypeVar("T")

logger = logging.getLogger(__name__)


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
