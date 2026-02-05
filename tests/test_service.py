"""
Tests for the service module in src/service.py
"""
import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

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


class TestSelectUserForService:
    """Tests for select_user_for_service function."""

    @patch('src.service.console')
    def test_select_user_no_users_exits(self, mock_console, temp_db):
        """Test that function exits if no users configured."""
        from src.service import select_user_for_service

        with pytest.raises(SystemExit):
            select_user_for_service()

    @patch('src.service.console')
    def test_select_user_single_user_auto_select(self, mock_console, temp_db):
        """Test auto-selection when only one user exists."""
        from src.service import select_user_for_service

        temp_db['db'].upsert_user("only_user", "pass", "https://x.com", [])

        result = select_user_for_service()

        assert result['username'] == "only_user"

    @patch('src.service.console')
    def test_select_user_specific_user_by_username(self, mock_console, temp_db):
        """Test selecting specific user by username."""
        from src.service import select_user_for_service

        temp_db['db'].upsert_user("user1", "pass", "https://x.com", [])
        temp_db['db'].upsert_user("user2", "pass", "https://x.com", [])

        result = select_user_for_service(specific_user="user2")

        assert result['username'] == "user2"

    @patch('src.service.console')
    def test_select_user_specific_user_by_real_name(self, mock_console, temp_db):
        """Test selecting specific user by real name."""
        from src.service import select_user_for_service

        temp_db['db'].upsert_user("user1", "pass", "https://x.com", [], real_name="Max Mustermann")
        temp_db['db'].upsert_user("user2", "pass", "https://x.com", [], real_name="Erika Musterfrau")

        result = select_user_for_service(specific_user="max")

        assert result['username'] == "user1"

    @patch('src.service.console')
    def test_select_user_specific_user_not_found_exits(self, mock_console, temp_db):
        """Test exit when specific user not found."""
        from src.service import select_user_for_service

        temp_db['db'].upsert_user("user1", "pass", "https://x.com", [])

        with pytest.raises(SystemExit):
            select_user_for_service(specific_user="nonexistent")


class TestGetInstalledServices:
    """Tests for get_installed_services function."""

    @patch('src.service.platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_get_installed_services_linux(self, mock_run, mock_system):
        """Test getting installed services on Linux."""
        from src.service import get_installed_services

        mock_run.return_value = MagicMock(
            stdout="incode-bot-user1.service loaded active running\nincode-bot-user2.service loaded active running\n"
        )

        services = get_installed_services()

        assert 'user1' in services
        assert 'user2' in services

    @patch('src.service.platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_get_installed_services_linux_empty(self, mock_run, mock_system):
        """Test getting installed services on Linux when none exist."""
        from src.service import get_installed_services

        mock_run.return_value = MagicMock(stdout="")

        services = get_installed_services()

        assert services == []

    @patch('src.service.platform.system', return_value='Darwin')
    @patch('os.path.exists', return_value=True)
    @patch('glob.glob')
    def test_get_installed_services_macos(self, mock_glob, mock_exists, mock_system):
        """Test getting installed services on macOS."""
        from src.service import get_installed_services

        mock_glob.return_value = [
            '/Users/test/Library/LaunchAgents/com.incode.bot.user1.plist',
            '/Users/test/Library/LaunchAgents/com.incode.bot.user2.plist'
        ]

        services = get_installed_services()

        assert 'user1' in services
        assert 'user2' in services

    @patch('src.service.platform.system', return_value='Windows')
    def test_get_installed_services_unsupported_os(self, mock_system):
        """Test getting installed services on unsupported OS."""
        from src.service import get_installed_services

        services = get_installed_services()

        assert services == []


class TestHasInstalledServices:
    """Tests for has_installed_services function."""

    @patch('src.service.get_installed_services', return_value=['user1'])
    def test_has_installed_services_true(self, mock_get):
        """Test has_installed_services returns True when services exist."""
        from src.service import has_installed_services

        assert has_installed_services() is True

    @patch('src.service.get_installed_services', return_value=[])
    def test_has_installed_services_false(self, mock_get):
        """Test has_installed_services returns False when no services."""
        from src.service import has_installed_services

        assert has_installed_services() is False


class TestInstallService:
    """Tests for install_service function."""

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Windows')
    def test_install_service_unsupported_os(self, mock_system, mock_console, temp_db):
        """Test install_service on unsupported OS."""
        from src.service import install_service

        install_service()

        # Should print error about unsupported OS
        mock_console.print.assert_called()
        calls = str(mock_console.print.call_args_list)
        assert 'nicht unterstützt' in calls or 'Windows' in calls

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Linux')
    @patch('os.path.exists', return_value=False)
    def test_install_service_linux_no_venv(self, mock_exists, mock_system, mock_console, temp_db):
        """Test install_service fails without venv."""
        from src.service import install_service

        temp_db['db'].upsert_user("testuser", "pass", "https://x.com", [])

        install_service()

        # Should print error about missing venv
        mock_console.print.assert_called()


class TestUninstallService:
    """Tests for uninstall_service function."""

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Windows')
    def test_uninstall_service_unsupported_os(self, mock_system, mock_console):
        """Test uninstall_service on unsupported OS."""
        from src.service import uninstall_service

        uninstall_service()

        mock_console.print.assert_called()

    @patch('src.service.console')
    @patch('src.service.get_installed_services', return_value=[])
    @patch('src.service.platform.system', return_value='Linux')
    def test_uninstall_service_no_services(self, mock_system, mock_get, mock_console):
        """Test uninstall_service when no services installed."""
        from src.service import uninstall_service

        uninstall_service()

        # Should print message about no services
        mock_console.print.assert_called()


class TestCheckServiceStatus:
    """Tests for check_service_status function."""

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_check_service_status_linux(self, mock_run, mock_system, mock_console):
        """Test checking service status on Linux."""
        from src.service import check_service_status

        mock_run.return_value = MagicMock(stdout="incode-bot-user1.service loaded active running")

        check_service_status()

        mock_run.assert_called()
        mock_console.print.assert_called()

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Darwin')
    @patch('subprocess.run')
    def test_check_service_status_macos(self, mock_run, mock_system, mock_console):
        """Test checking service status on macOS."""
        from src.service import check_service_status

        mock_run.return_value = MagicMock(stdout="123 0 com.incode.bot.user1")

        check_service_status()

        mock_run.assert_called()
        mock_console.print.assert_called()

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Windows')
    def test_check_service_status_unsupported(self, mock_system, mock_console):
        """Test checking service status on unsupported OS."""
        from src.service import check_service_status

        check_service_status()

        mock_console.print.assert_called()


class TestRestartServices:
    """Tests for restart_services function."""

    @patch('src.service.console')
    @patch('src.service.get_installed_services', return_value=[])
    def test_restart_no_services(self, mock_get, mock_console):
        """Test restart when no services installed."""
        from src.service import restart_services

        restart_services()

        # Should not print anything (early return)

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Linux')
    @patch('src.service.get_installed_services', return_value=['user1'])
    @patch('os.geteuid', return_value=0)
    @patch('subprocess.run')
    def test_restart_linux_as_root(self, mock_run, mock_euid, mock_get, mock_system, mock_console):
        """Test restart on Linux as root."""
        from src.service import restart_services

        mock_run.return_value = MagicMock(returncode=0)

        restart_services()

        mock_run.assert_called()
        # Verify systemctl restart was called
        call_args = mock_run.call_args_list[0][0][0]
        assert 'systemctl' in call_args
        assert 'restart' in call_args

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Darwin')
    @patch('src.service.get_installed_services', return_value=['user1'])
    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    def test_restart_macos(self, mock_run, mock_exists, mock_get, mock_system, mock_console):
        """Test restart on macOS."""
        from src.service import restart_services

        mock_run.return_value = MagicMock(returncode=0)

        restart_services()

        # Verify launchctl unload/load were called
        calls = mock_run.call_args_list
        assert len(calls) >= 2  # unload + load
        unload_call = str(calls[0])
        load_call = str(calls[1])
        assert 'unload' in unload_call
        assert 'load' in load_call

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Linux')
    @patch('src.service.get_installed_services', return_value=['user1'])
    @patch('os.geteuid', return_value=1000)
    @patch('subprocess.run')
    def test_restart_linux_non_root_uses_sudo(self, mock_run, mock_euid, mock_get, mock_system, mock_console):
        """Test restart on Linux as non-root uses sudo."""
        from src.service import restart_services

        mock_run.return_value = MagicMock(returncode=0)

        restart_services()

        call_args = mock_run.call_args_list[0][0][0]
        assert 'sudo' in call_args


class TestInstallSystemdServiceAsRoot:
    """Tests that install_systemd_service uses subprocess.run instead of os.system."""

    @patch('src.service.console')
    @patch('os.geteuid', return_value=0)
    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=MagicMock)
    def test_install_systemd_calls_subprocess_run(self, mock_open, mock_run, mock_exists, mock_euid, mock_console):
        """Test that systemctl commands use subprocess.run with list args."""
        from src.service import install_systemd_service

        bot_user = {'username': 'testuser', 'password': 'pass', 'base_url': 'https://x.com'}
        install_systemd_service(bot_user)

        # Verify subprocess.run was called (not os.system)
        assert mock_run.call_count == 3

        # Verify all calls use list arguments (no shell injection possible)
        calls = mock_run.call_args_list
        assert calls[0][0][0] == ["systemctl", "daemon-reload"]
        assert calls[1][0][0] == ["systemctl", "enable", "incode-bot-testuser.service"]
        assert calls[2][0][0] == ["systemctl", "start", "incode-bot-testuser.service"]


class TestUninstallServiceAsRoot:
    """Tests that uninstall_service uses subprocess.run on Linux."""

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Linux')
    @patch('src.service.get_installed_services', return_value=['testuser'])
    @patch('os.geteuid', return_value=0)
    @patch('os.path.exists', return_value=True)
    @patch('os.remove')
    @patch('subprocess.run')
    def test_uninstall_linux_root_calls_subprocess_run(self, mock_run, mock_remove, mock_exists, mock_euid, mock_get, mock_system, mock_console):
        """Test that uninstall uses subprocess.run with list args for systemctl."""
        from src.service import uninstall_service

        uninstall_service()

        # Verify subprocess.run was called for stop, disable, daemon-reload
        assert mock_run.call_count == 3
        calls = mock_run.call_args_list
        assert calls[0][0][0] == ["systemctl", "stop", "incode-bot-testuser.service"]
        assert calls[1][0][0] == ["systemctl", "disable", "incode-bot-testuser.service"]
        assert calls[2][0][0] == ["systemctl", "daemon-reload"]

    @patch('src.service.console')
    @patch('src.service.platform.system', return_value='Darwin')
    @patch('src.service.get_installed_services', return_value=['testuser'])
    @patch('os.path.exists', return_value=True)
    @patch('os.remove')
    @patch('subprocess.run')
    def test_uninstall_macos_calls_subprocess_run(self, mock_run, mock_remove, mock_exists, mock_get, mock_system, mock_console):
        """Test that uninstall uses subprocess.run for launchctl unload."""
        from src.service import uninstall_service

        uninstall_service()

        assert mock_run.call_count == 1
        call_args = mock_run.call_args_list[0][0][0]
        assert call_args[0] == "launchctl"
        assert call_args[1] == "unload"
        assert "com.incode.bot.testuser.plist" in call_args[2]


class TestInstallLaunchdService:
    """Tests that install_launchd_service uses subprocess.run."""

    @patch('src.service.console')
    @patch('os.path.exists', return_value=True)
    @patch('os.makedirs')
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=MagicMock)
    def test_install_launchd_calls_subprocess_run(self, mock_open, mock_run, mock_makedirs, mock_exists, mock_console):
        """Test that launchctl load uses subprocess.run with list args."""
        from src.service import install_launchd_service

        bot_user = {'username': 'testuser', 'password': 'pass', 'base_url': 'https://x.com'}
        install_launchd_service(bot_user)

        # Verify subprocess.run was called for launchctl load
        assert mock_run.call_count == 1
        call_args = mock_run.call_args_list[0][0][0]
        assert call_args[0] == "launchctl"
        assert call_args[1] == "load"
        assert "com.incode.bot.testuser.plist" in call_args[2]


class TestNoOsSystemCalls:
    """Verify os.system is never called in service module operations."""

    @patch('src.service.console')
    @patch('os.geteuid', return_value=0)
    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.system')
    def test_install_systemd_never_calls_os_system(self, mock_os_system, mock_open, mock_run, mock_exists, mock_euid, mock_console):
        """Ensure os.system is never called during systemd install."""
        from src.service import install_systemd_service

        bot_user = {'username': 'testuser', 'password': 'pass', 'base_url': 'https://x.com'}
        install_systemd_service(bot_user)

        mock_os_system.assert_not_called()
