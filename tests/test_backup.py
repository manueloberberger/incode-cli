"""
Tests for the backup module in src/backup.py
"""
import pytest
import os
import sys
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.db as db_module


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_incode.db")

    original_db_file = db_module.DB_FILE
    db_module.DB_FILE = temp_db_path

    db_module.DatabaseManager._instance = None
    db_module.DatabaseManager._initialized = False

    db = db_module.DatabaseManager()

    original_db = db_module.db
    db_module.db = db

    yield {'db': db, 'temp_dir': temp_dir}

    db_module.DB_FILE = original_db_file
    db_module.db = original_db
    db_module.DatabaseManager._instance = None
    db_module.DatabaseManager._initialized = False
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestExportData:
    """Tests for export_data function."""

    @patch('src.backup.console')
    def test_export_empty_database(self, mock_console, temp_db):
        """Test exporting an empty database."""
        from src.backup import export_data

        export_path = os.path.join(temp_db['temp_dir'], "backup.json")

        result = export_data(export_path)

        assert result is True
        assert os.path.exists(export_path)

        with open(export_path, 'r') as f:
            data = json.load(f)

        assert 'meta' in data
        assert 'users' in data
        assert 'valuestore' in data
        assert data['users'] == []

    @patch('src.backup.console')
    def test_export_with_users(self, mock_console, temp_db):
        """Test exporting database with users."""
        from src.backup import export_data

        # Add some users
        temp_db['db'].upsert_user("user1", "pass1", "https://a.com", ["guid1"], "User One")
        temp_db['db'].upsert_user("user2", "pass2", "https://b.com", [], "User Two")

        export_path = os.path.join(temp_db['temp_dir'], "backup.json")
        result = export_data(export_path)

        assert result is True

        with open(export_path, 'r') as f:
            data = json.load(f)

        assert len(data['users']) == 2
        usernames = [u['username'] for u in data['users']]
        assert 'user1' in usernames
        assert 'user2' in usernames

    @patch('src.backup.console')
    def test_export_with_settings(self, mock_console, temp_db):
        """Test exporting database with settings."""
        from src.backup import export_data

        # Add some settings
        temp_db['db'].set_value("setting1", "value1")
        temp_db['db'].set_value("setting2", {"complex": "data"})

        export_path = os.path.join(temp_db['temp_dir'], "backup.json")
        result = export_data(export_path)

        assert result is True

        with open(export_path, 'r') as f:
            data = json.load(f)

        assert data['valuestore']['setting1'] == "value1"
        assert data['valuestore']['setting2'] == {"complex": "data"}

    @patch('src.backup.console')
    def test_export_invalid_path(self, mock_console, temp_db):
        """Test export to invalid path."""
        from src.backup import export_data

        result = export_data("/nonexistent/path/backup.json")

        assert result is False
        mock_console.print.assert_called()


class TestImportData:
    """Tests for import_data function."""

    @patch('src.backup.console')
    def test_import_valid_backup(self, mock_console, temp_db):
        """Test importing a valid backup file."""
        from src.backup import import_data

        # Create backup file
        backup_data = {
            'meta': {'version': 1, 'timestamp': 0},
            'users': [
                {'username': 'imported_user', 'password': 'pass', 'base_url': 'https://x.com', 'extra_guids': []}
            ],
            'valuestore': {'imported_setting': 'imported_value'}
        }

        backup_path = os.path.join(temp_db['temp_dir'], "backup.json")
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f)

        result = import_data(backup_path)

        assert result is True

        # Verify user was imported
        user = temp_db['db'].get_user('imported_user')
        assert user is not None
        assert user['password'] == 'pass'

        # Verify setting was imported
        setting = temp_db['db'].get_value('imported_setting')
        assert setting == 'imported_value'

    @patch('src.backup.console')
    def test_import_merges_with_existing(self, mock_console, temp_db):
        """Test that import merges with existing data."""
        from src.backup import import_data

        # Add existing user
        temp_db['db'].upsert_user("existing_user", "pass", "https://x.com", [])

        # Import new user
        backup_data = {
            'meta': {'version': 1},
            'users': [{'username': 'new_user', 'password': 'pass', 'base_url': 'https://y.com', 'extra_guids': []}],
            'valuestore': {}
        }

        backup_path = os.path.join(temp_db['temp_dir'], "backup.json")
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f)

        import_data(backup_path)

        # Both users should exist
        assert temp_db['db'].get_user('existing_user') is not None
        assert temp_db['db'].get_user('new_user') is not None

    @patch('src.backup.console')
    def test_import_updates_existing_user(self, mock_console, temp_db):
        """Test that import updates existing users."""
        from src.backup import import_data

        # Add existing user
        temp_db['db'].upsert_user("testuser", "oldpass", "https://old.com", [])

        # Import with updated data
        backup_data = {
            'meta': {'version': 1},
            'users': [{'username': 'testuser', 'password': 'newpass', 'base_url': 'https://new.com', 'extra_guids': [], 'real_name': 'Updated'}],
            'valuestore': {}
        }

        backup_path = os.path.join(temp_db['temp_dir'], "backup.json")
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f)

        import_data(backup_path)

        user = temp_db['db'].get_user('testuser')
        assert user['password'] == 'newpass'
        assert user['base_url'] == 'https://new.com'
        assert user['real_name'] == 'Updated'

    @patch('src.backup.console')
    def test_import_file_not_found(self, mock_console, temp_db):
        """Test import with nonexistent file."""
        from src.backup import import_data

        result = import_data("/nonexistent/backup.json")

        assert result is False
        mock_console.print.assert_called()

    @patch('src.backup.console')
    def test_import_invalid_json(self, mock_console, temp_db):
        """Test import with invalid JSON file."""
        from src.backup import import_data

        invalid_path = os.path.join(temp_db['temp_dir'], "invalid.json")
        with open(invalid_path, 'w') as f:
            f.write("not valid json {{{")

        result = import_data(invalid_path)

        assert result is False

    @patch('src.backup.console')
    def test_import_skips_users_without_username(self, mock_console, temp_db):
        """Test that users without username are skipped."""
        from src.backup import import_data

        backup_data = {
            'meta': {'version': 1},
            'users': [
                {'password': 'pass'},  # No username
                {'username': 'valid_user', 'password': 'pass', 'base_url': 'https://x.com', 'extra_guids': []}
            ],
            'valuestore': {}
        }

        backup_path = os.path.join(temp_db['temp_dir'], "backup.json")
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f)

        import_data(backup_path)

        users = temp_db['db'].get_users()
        assert len(users) == 1
        assert users[0]['username'] == 'valid_user'
