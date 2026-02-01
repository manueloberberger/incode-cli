"""
Tests for the bot module in src/bot.py
"""
import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.db as db_module
import src.config as config_module


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_incode.db")

    original_db_file = db_module.DB_FILE
    db_module.DB_FILE = temp_db_path

    # Use reset_instance to properly close connections
    db_module.DatabaseManager.reset_instance()

    db = db_module.DatabaseManager()

    # Patch the global db instance in all modules that import it
    original_db = db_module.db
    original_config_db = config_module.db
    db_module.db = db
    config_module.db = db

    yield {'db': db, 'temp_dir': temp_dir}

    db_module.DB_FILE = original_db_file
    db_module.db = original_db
    config_module.db = original_config_db
    db_module.DatabaseManager.reset_instance()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_api():
    """Create a mock API instance."""
    api = MagicMock()
    api.username = "testuser"
    api.header_key = "x-incode-test"
    api.header_value = "token123"
    api.discovered_name = "Test User"
    api.load_future_duties.return_value = []
    api.load_daily_plan.return_value = []
    return api


class TestConflictFilter:
    """Tests for the ConflictFilter class."""

    def test_filter_passes_normal_log(self):
        """Test that normal logs are passed through."""
        from src.bot import ConflictFilter
        import logging

        filter_instance = ConflictFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="Normal message",
            args=(), exc_info=None
        )

        result = filter_instance.filter(record)

        assert result is True

    def test_filter_blocks_conflict_message(self):
        """Test that Conflict messages are blocked."""
        from src.bot import ConflictFilter
        import logging

        filter_instance = ConflictFilter()
        record = logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname="", lineno=0, msg="Conflict occurred",
            args=(), exc_info=None
        )

        result = filter_instance.filter(record)

        assert result is False

    def test_filter_calls_callback_on_conflict(self):
        """Test that callback is called on conflict."""
        from src.bot import ConflictFilter
        import logging

        callback = MagicMock()
        filter_instance = ConflictFilter(on_conflict_callback=callback)

        record = logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname="", lineno=0, msg="Conflict detected",
            args=(), exc_info=None
        )

        filter_instance.filter(record)

        callback.assert_called_once()

    def test_filter_handles_callback_exception(self):
        """Test that callback exceptions are handled."""
        from src.bot import ConflictFilter
        import logging

        callback = MagicMock(side_effect=RuntimeError("Callback error"))
        filter_instance = ConflictFilter(on_conflict_callback=callback)

        record = logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname="", lineno=0, msg="Conflict detected",
            args=(), exc_info=None
        )

        # Should not raise
        result = filter_instance.filter(record)

        assert result is False


class TestIncodeBotInit:
    """Tests for IncodeBot initialization."""

    @patch('src.bot.centered_input', return_value=None)
    @patch('src.bot.console')
    def test_bot_creation_without_config(self, mock_console, mock_input, temp_db, mock_api):
        """Test bot creation when config is missing (aborts)."""
        from src.bot import IncodeBot

        # No telegram config saved
        bot = IncodeBot(mock_api)

        # Should have prompted for config
        mock_input.assert_called()

    @patch('src.bot.console')
    def test_bot_creation_with_config(self, mock_console, temp_db, mock_api):
        """Test bot creation with existing config."""
        from src.bot import IncodeBot

        # Save telegram config
        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[],
            telegram_token="123:ABC",
            allowed_user_id=12345
        )

        bot = IncodeBot(mock_api)

        assert bot.user_config.get('telegram_token') == "123:ABC"
        assert bot.user_config.get('allowed_user_id') == 12345

    @patch('src.bot.console')
    def test_get_active_user_config(self, mock_console, temp_db, mock_api):
        """Test _get_active_user_config method."""
        from src.bot import IncodeBot

        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[],
            telegram_token="token",
            allowed_user_id=999
        )

        bot = IncodeBot(mock_api)
        config = bot._get_active_user_config()

        assert config['username'] == "testuser"


class TestIncodeBotSendDocument:
    """Tests for send_document functionality."""

    @patch('src.bot.centered_input', return_value=None)
    @patch('src.bot.console')
    def test_send_document_no_token(self, mock_console, mock_input, temp_db, mock_api):
        """Test send_document returns False without token."""
        from src.bot import IncodeBot

        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[]
        )

        bot = IncodeBot(mock_api)
        bot.user_config = {}  # Clear config

        result = bot.send_document(12345, "test.pdf", "caption")

        assert result is False


class TestIncodeBotFetchDuties:
    """Tests for _fetch_duties_sync method."""

    @patch('src.bot.console')
    def test_fetch_duties_calls_load_future_duties(self, mock_console, temp_db, mock_api):
        """Test that _fetch_duties_sync calls correct API method."""
        from src.bot import IncodeBot

        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[],
            telegram_token="token",
            allowed_user_id=123
        )

        bot = IncodeBot(mock_api)

        result = bot._fetch_duties_sync(filter_today=False)

        mock_api.load_future_duties.assert_called_once()

    @patch('src.bot.console')
    def test_fetch_duties_calls_load_daily_plan_for_today(self, mock_console, temp_db, mock_api):
        """Test that filter_today=True calls load_daily_plan."""
        from src.bot import IncodeBot

        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[],
            telegram_token="token",
            allowed_user_id=123
        )

        bot = IncodeBot(mock_api)

        result = bot._fetch_duties_sync(filter_today=True)

        mock_api.load_daily_plan.assert_called_once()

    @patch('src.bot.console')
    def test_fetch_duties_with_custom_date(self, mock_console, temp_db, mock_api):
        """Test fetch with custom date."""
        from src.bot import IncodeBot
        from datetime import datetime

        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[],
            telegram_token="token",
            allowed_user_id=123
        )

        custom_date = datetime(2024, 6, 15)
        bot = IncodeBot(mock_api)

        result = bot._fetch_duties_sync(filter_today=False, custom_date=custom_date)

        mock_api.load_daily_plan.assert_called_once_with(custom_date)


class TestIncodeBotHelpCommand:
    """Tests for the help command."""

    @pytest.mark.asyncio
    @patch('src.bot.console')
    async def test_help_command_sends_help_text(self, mock_console, temp_db, mock_api):
        """Test that help command sends help message."""
        from src.bot import IncodeBot

        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[],
            telegram_token="token",
            allowed_user_id=123
        )

        bot = IncodeBot(mock_api)

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message = AsyncMock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = MagicMock()

        from src.bot import ConversationHandler
        result = await bot.help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        help_text = call_args[0][0]

        # Verify help content
        assert "/start" in help_text
        assert "/dienste" in help_text
        assert "/tagesplan" in help_text
        assert "/help" in help_text
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    @patch('src.bot.console')
    async def test_help_command_no_message(self, mock_console, temp_db, mock_api):
        """Test help command with no message returns END."""
        from src.bot import IncodeBot, ConversationHandler

        temp_db['db'].upsert_user(
            username="testuser",
            password="pass",
            base_url="https://x.com",
            extra_guids=[],
            telegram_token="token",
            allowed_user_id=123
        )

        bot = IncodeBot(mock_api)

        mock_update = MagicMock()
        mock_update.message = None
        mock_context = MagicMock()

        result = await bot.help_command(mock_update, mock_context)

        assert result == ConversationHandler.END
