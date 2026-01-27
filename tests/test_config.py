"""
Tests for the config module in src/config.py
"""
import pytest
import os
import sys
import tempfile
import shutil

# Add project root to path
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

    # Patch the global db instance used by both db module and config module
    original_db = db_module.db
    original_config_db = config_module.db
    db_module.db = db
    config_module.db = db

    yield db

    db_module.DB_FILE = original_db_file
    db_module.db = original_db
    config_module.db = original_config_db
    db_module.DatabaseManager.reset_instance()
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestCredentialFunctions:
    """Tests for credential management functions."""

    def test_load_credentials_empty(self, temp_db):
        """Test loading credentials when no users exist."""
        from src.config import load_credentials

        result = load_credentials()

        assert 'users' in result
        assert result['users'] == []
        assert result['last_active'] is None

    def test_save_and_load_credentials(self, temp_db):
        """Test saving and loading credentials."""
        from src.config import save_credentials, load_credentials

        save_credentials(
            username="testuser",
            password="testpass",
            base_url="https://example.com",
            extra_guids=["guid1"],
            real_name="Test User"
        )

        result = load_credentials()

        assert len(result['users']) == 1
        assert result['users'][0]['username'] == "testuser"
        assert result['users'][0]['password'] == "testpass"
        assert result['last_active'] == "testuser"

    def test_save_credentials_sets_active(self, temp_db):
        """Test that save_credentials sets the user as active."""
        from src.config import save_credentials, load_credentials

        save_credentials("user1", "pass1", "https://a.com")
        save_credentials("user2", "pass2", "https://b.com")

        result = load_credentials()

        # Last saved user should be active
        assert result['last_active'] == "user2"

    def test_remove_user(self, temp_db):
        """Test removing a user."""
        from src.config import save_credentials, remove_user, load_credentials

        save_credentials("user1", "pass1", "https://a.com")
        save_credentials("user2", "pass2", "https://b.com")

        remove_user("user2")

        result = load_credentials()

        assert len(result['users']) == 1
        assert result['users'][0]['username'] == "user1"

    def test_remove_active_user_updates_active(self, temp_db):
        """Test that removing active user updates last_active."""
        from src.config import save_credentials, remove_user, load_credentials

        save_credentials("user1", "pass1", "https://a.com")
        save_credentials("user2", "pass2", "https://b.com")  # user2 is now active

        remove_user("user2")  # Remove active user

        result = load_credentials()

        # Should fall back to remaining user
        assert result['last_active'] == "user1"

    def test_update_credentials(self, temp_db):
        """Test updating user credentials."""
        from src.config import save_credentials, update_credentials, load_credentials

        save_credentials("testuser", "oldpass", "https://old.com")

        update_credentials({'real_name': 'New Name'}, username="testuser")

        result = load_credentials()
        user = result['users'][0]

        assert user['real_name'] == 'New Name'
        # Other fields should be preserved
        assert user['password'] == 'oldpass'

    def test_update_credentials_active_user(self, temp_db):
        """Test updating credentials without specifying username uses active user."""
        from src.config import save_credentials, update_credentials, load_credentials

        save_credentials("testuser", "pass", "https://x.com")

        update_credentials({'real_name': 'Updated Name'})

        result = load_credentials()

        assert result['users'][0]['real_name'] == 'Updated Name'


class TestSettingsFunctions:
    """Tests for settings-related functions."""

    def test_update_interval_default(self, temp_db):
        """Test default update interval."""
        from src.config import get_update_interval

        interval = get_update_interval()

        assert interval == 21600  # 6 hours default

    def test_set_and_get_update_interval(self, temp_db):
        """Test setting and getting update interval."""
        from src.config import set_update_interval, get_update_interval

        set_update_interval(3600)  # 1 hour

        assert get_update_interval() == 3600

    def test_last_update_check_default(self, temp_db):
        """Test default last update check."""
        from src.config import get_last_update_check

        check = get_last_update_check()

        assert check == 0.0

    def test_set_and_get_last_update_check(self, temp_db):
        """Test setting and getting last update check."""
        from src.config import set_last_update_check, get_last_update_check
        import time

        now = time.time()
        set_last_update_check(now)

        assert get_last_update_check() == now


class TestStorageStatus:
    """Tests for storage status function."""

    def test_get_storage_status(self, temp_db):
        """Test getting storage status."""
        from src.config import get_storage_status

        status = get_storage_status("anyuser")

        # Should always return SQLite for this implementation
        assert status == "SQLite"
