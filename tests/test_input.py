"""
Tests for the input module in src/input.py
"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestKeyConstants:
    """Tests for key constants."""

    def test_key_constants_defined(self):
        """Test that key constants are properly defined."""
        from src.input import (
            KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,
            KEY_UP_ALT, KEY_DOWN_ALT, KEY_LEFT_ALT, KEY_RIGHT_ALT,
            KEY_ENTER, KEY_ESC, KEY_BACKSPACE
        )

        assert KEY_UP == '\x1b[A'
        assert KEY_DOWN == '\x1b[B'
        assert KEY_RIGHT == '\x1b[C'
        assert KEY_LEFT == '\x1b[D'
        assert KEY_ENTER == '\r'
        assert KEY_ESC == '\x1b'
        assert KEY_BACKSPACE == '\x7f'


class TestUnicodeLen:
    """Tests for unicode_len function."""

    def test_unicode_len_simple(self):
        """Test unicode_len with simple string."""
        from src.input import unicode_len

        assert unicode_len("Hello") == 5
        assert unicode_len("") == 0
        assert unicode_len("Test 123") == 8

    def test_unicode_len_with_ansi(self):
        """Test unicode_len strips ANSI codes."""
        from src.input import unicode_len

        # ANSI bold code: \x1b[1m ... \x1b[0m
        ansi_string = "\x1b[1mBold\x1b[0m"

        length = unicode_len(ansi_string)

        # Should only count "Bold", not ANSI codes
        assert length == 4

    def test_unicode_len_with_color(self):
        """Test unicode_len with color codes."""
        from src.input import unicode_len

        # ANSI red color: \x1b[31m ... \x1b[0m
        colored = "\x1b[31mRed Text\x1b[0m"

        length = unicode_len(colored)

        assert length == 8  # "Red Text"


class TestFlushInput:
    """Tests for flush_input function."""

    @patch('src.input.os.name', 'posix')
    @patch('src.input.termios')
    def test_flush_input_unix(self, mock_termios):
        """Test flush_input on Unix systems."""
        from src.input import flush_input

        flush_input()

        mock_termios.tcflush.assert_called()


class TestClearScreen:
    """Tests for clear_screen function."""

    @patch('src.input.os.system')
    @patch('src.input.os.name', 'posix')
    def test_clear_screen_unix(self, mock_system):
        """Test clear_screen on Unix systems."""
        from src.input import clear_screen

        clear_screen()

        mock_system.assert_called_once_with('clear')

    @patch('src.input.os.system')
    @patch('src.input.os.name', 'nt')
    def test_clear_screen_windows(self, mock_system):
        """Test clear_screen on Windows systems."""
        from src.input import clear_screen

        clear_screen()

        mock_system.assert_called_once_with('cls')


class TestGetKey:
    """Tests for get_key function."""

    @patch('src.input.os.name', 'posix')
    @patch('src.input._get_key_unix')
    def test_get_key_routes_to_unix(self, mock_unix):
        """Test get_key routes to Unix implementation."""
        from src.input import get_key

        mock_unix.return_value = 'a'

        result = get_key(timeout=1.0)

        mock_unix.assert_called_once_with(1.0)


class TestWaitForReturn:
    """Tests for wait_for_return function."""

    @patch('src.input.get_key')
    @patch('src.input.flush_input')
    @patch('src.input.console')
    def test_wait_for_return_returns_key(self, mock_console, mock_flush, mock_get_key):
        """Test wait_for_return returns the key pressed."""
        from src.input import wait_for_return

        mock_get_key.return_value = 'x'

        result = wait_for_return()

        assert result == 'x'
        mock_flush.assert_called_once()


class TestPromptYesNo:
    """Tests for prompt_yes_no function."""

    @patch('src.input.get_key')
    @patch('src.input.console')
    def test_prompt_yes_no_enter_on_yes(self, mock_console, mock_get_key):
        """Test prompt_yes_no returns True when Enter on Yes."""
        from src.input import prompt_yes_no, KEY_ENTER

        # First get_key returns Enter (default is Yes)
        mock_get_key.return_value = KEY_ENTER

        result = prompt_yes_no("Test question?")

        assert result is True

    @patch('src.input.get_key')
    @patch('src.input.console')
    def test_prompt_yes_no_navigation_to_no(self, mock_console, mock_get_key):
        """Test prompt_yes_no navigation to No."""
        from src.input import prompt_yes_no, KEY_RIGHT, KEY_ENTER

        # Navigate right (to No), then Enter
        mock_get_key.side_effect = [KEY_RIGHT, KEY_ENTER]

        result = prompt_yes_no("Test question?")

        assert result is False

    @patch('src.input.get_key')
    @patch('src.input.console')
    def test_prompt_yes_no_escape_returns_false(self, mock_console, mock_get_key):
        """Test prompt_yes_no returns False on Escape."""
        from src.input import prompt_yes_no, KEY_ESC

        mock_get_key.return_value = KEY_ESC

        result = prompt_yes_no("Test question?")

        assert result is False

    @patch('src.input.get_key')
    @patch('src.input.console')
    def test_prompt_yes_no_q_returns_false(self, mock_console, mock_get_key):
        """Test prompt_yes_no returns False on 'q'."""
        from src.input import prompt_yes_no

        mock_get_key.return_value = 'q'

        result = prompt_yes_no("Test question?")

        assert result is False


class TestCenteredInput:
    """Tests for centered_input function."""

    @patch('src.input.get_key')
    @patch('src.input.console')
    @patch('src.input.shutil.get_terminal_size')
    @patch('sys.stdout', new_callable=MagicMock)
    def test_centered_input_basic(self, mock_stdout, mock_size, mock_console, mock_get_key):
        """Test centered_input with basic input."""
        from src.input import centered_input, KEY_ENTER

        mock_size.return_value = MagicMock(columns=80)
        # Type 'test' then Enter
        mock_get_key.side_effect = ['t', 'e', 's', 't', KEY_ENTER]

        result = centered_input("Label: ")

        assert result == "test"

    @patch('src.input.get_key')
    @patch('src.input.console')
    @patch('src.input.shutil.get_terminal_size')
    @patch('sys.stdout', new_callable=MagicMock)
    def test_centered_input_escape_returns_none(self, mock_stdout, mock_size, mock_console, mock_get_key):
        """Test centered_input returns None on Escape."""
        from src.input import centered_input, KEY_ESC

        mock_size.return_value = MagicMock(columns=80)
        mock_get_key.return_value = KEY_ESC

        result = centered_input("Label: ")

        assert result is None

    @patch('src.input.get_key')
    @patch('src.input.console')
    @patch('src.input.shutil.get_terminal_size')
    @patch('sys.stdout', new_callable=MagicMock)
    def test_centered_input_with_default(self, mock_stdout, mock_size, mock_console, mock_get_key):
        """Test centered_input returns default on empty input."""
        from src.input import centered_input, KEY_ENTER

        mock_size.return_value = MagicMock(columns=80)
        mock_get_key.return_value = KEY_ENTER  # Just press enter

        result = centered_input("Label: ", default="default_value")

        assert result == "default_value"

    @patch('src.input.get_key')
    @patch('src.input.console')
    @patch('src.input.shutil.get_terminal_size')
    @patch('sys.stdout', new_callable=MagicMock)
    def test_centered_input_backspace(self, mock_stdout, mock_size, mock_console, mock_get_key):
        """Test centered_input handles backspace."""
        from src.input import centered_input, KEY_ENTER, KEY_BACKSPACE

        mock_size.return_value = MagicMock(columns=80)
        # Type 'ab', backspace, 'c', Enter -> should result in 'ac'
        mock_get_key.side_effect = ['a', 'b', KEY_BACKSPACE, 'c', KEY_ENTER]

        result = centered_input("Label: ")

        assert result == "ac"
