"""
Tests for the updates module.
"""
import os
import time
import pytest
from unittest.mock import patch, MagicMock
import subprocess

from src.updates import check_for_updates, update_app


class TestCheckForUpdates:
    """Tests for check_for_updates function."""
    
    def test_no_git_directory(self, tmp_path, monkeypatch):
        """Should return None if no .git directory exists."""
        monkeypatch.chdir(tmp_path)
        result = check_for_updates(debug=False)
        assert result is None
    
    @patch('src.updates.os.path.exists')
    @patch('src.updates.get_last_update_check')
    @patch('src.updates.get_update_interval')
    def test_cache_prevents_check(self, mock_interval, mock_last_check, mock_exists):
        """Should return None if checked recently (within interval)."""
        mock_exists.return_value = True
        mock_last_check.return_value = time.time() - 100  # 100 seconds ago
        mock_interval.return_value = 3600  # 1 hour interval
        
        result = check_for_updates(debug=False, ignore_cache=False)
        assert result is None
    
    @patch('src.updates.os.path.exists')
    @patch('src.updates.subprocess.run')
    @patch('src.updates.get_last_update_check')
    @patch('src.updates.get_update_interval')
    @patch('src.updates.set_last_update_check')
    def test_no_updates_available(self, mock_set_check, mock_interval, mock_last_check, mock_run, mock_exists):
        """Should return None when no updates are available."""
        mock_exists.return_value = True
        mock_last_check.return_value = 0  # Never checked
        mock_interval.return_value = 3600
        
        # Mock git fetch success
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git fetch
            MagicMock(returncode=0, stdout='0')  # git rev-list (0 commits behind)
        ]
        
        result = check_for_updates(debug=False, ignore_cache=True)
        assert result is None
    
    @patch('src.updates.os.path.exists')
    @patch('src.updates.subprocess.run')
    @patch('src.updates.get_last_update_check')
    @patch('src.updates.get_update_interval')
    @patch('src.updates.set_last_update_check')
    def test_updates_available_with_version(self, mock_set_check, mock_interval, mock_last_check, mock_run, mock_exists):
        """Should return version string when updates are available."""
        mock_exists.return_value = True
        mock_last_check.return_value = 0
        mock_interval.return_value = 3600
        
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git fetch
            MagicMock(returncode=0, stdout='5'),  # 5 commits behind
            MagicMock(returncode=0, stdout='VERSION = "2.30.0"')  # config.py content
        ]
        
        result = check_for_updates(debug=False, ignore_cache=True)
        assert result == "2.30.0"
    
    @patch('src.updates.os.path.exists')
    @patch('src.updates.subprocess.run')
    @patch('src.updates.get_last_update_check')
    @patch('src.updates.get_update_interval')
    @patch('src.updates.set_last_update_check')
    def test_updates_available_fallback(self, mock_set_check, mock_interval, mock_last_check, mock_run, mock_exists):
        """Should return 'Neu' when update exists but version extraction fails."""
        mock_exists.return_value = True
        mock_last_check.return_value = 0
        mock_interval.return_value = 3600
        
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git fetch
            MagicMock(returncode=0, stdout='3'),  # 3 commits behind
            MagicMock(returncode=1, stdout='')  # git show fails
        ]
        
        result = check_for_updates(debug=False, ignore_cache=True)
        assert result == "Neu"
    
    @patch('src.updates.os.path.exists')
    @patch('src.updates.subprocess.run')
    def test_git_fetch_timeout(self, mock_run, mock_exists):
        """Should handle git fetch timeout gracefully."""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='git', timeout=10)
        
        result = check_for_updates(debug=True, ignore_cache=True)
        assert result is None


class TestUpdateApp:
    """Tests for update_app function."""
    
    @patch('src.updates.subprocess.run')
    @patch('src.updates.restart_services', create=True)
    def test_update_success_no_local_changes(self, mock_restart, mock_run):
        """Should successfully update when no local changes exist."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=''),  # git status (clean)
            MagicMock(returncode=0, stdout='abc123'),  # git rev-parse HEAD (before)
            MagicMock(returncode=0),  # git pull
            MagicMock(returncode=0, stdout='def456'),  # git rev-parse HEAD (after)
            MagicMock(returncode=0, stdout=''),  # git diff (no requirements change)
        ]
        
        with patch('src.updates.console'):
            with patch('src.updates.Live'):
                result = update_app()
        
        assert result is True
    
    @patch('src.updates.subprocess.run')
    @patch('src.updates.restart_services', create=True)
    def test_update_with_stash(self, mock_restart, mock_run):
        """Should stash and pop when local changes exist."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout='M file.py'),  # git status (dirty)
            MagicMock(returncode=0),  # git stash
            MagicMock(returncode=0, stdout='abc123'),  # git rev-parse HEAD (before)
            MagicMock(returncode=0),  # git pull
            MagicMock(returncode=0, stdout='', text=True),  # git stash pop
            MagicMock(returncode=0, stdout='def456'),  # git rev-parse HEAD (after)
            MagicMock(returncode=0, stdout=''),  # git diff
        ]
        
        with patch('src.updates.console'):
            with patch('src.updates.Live'):
                result = update_app()
        
        assert result is True
    
    @patch('src.updates.subprocess.run')
    def test_update_git_pull_fails(self, mock_run):
        """Should return False when git pull fails."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=''),  # git status (clean)
            MagicMock(returncode=0, stdout='abc123'),  # git rev-parse HEAD
            subprocess.CalledProcessError(1, 'git pull', stderr=b'error')  # git pull fails
        ]
        
        with patch('src.updates.console'):
            with patch('src.updates.Live'):
                result = update_app()
        
        assert result is False
    
    @patch('src.updates.subprocess.run')
    @patch('src.updates.restart_services', create=True)
    @patch('src.updates.sys.executable', '/usr/bin/python3')
    def test_update_with_requirements_change(self, mock_restart, mock_run):
        """Should run pip install when requirements.txt changed."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=''),  # git status (clean)
            MagicMock(returncode=0, stdout='abc123'),  # git rev-parse HEAD (before)
            MagicMock(returncode=0),  # git pull
            MagicMock(returncode=0, stdout='def456'),  # git rev-parse HEAD (after)
            MagicMock(returncode=0, stdout='requirements.txt\nREADME.md'),  # git diff
            MagicMock(returncode=0),  # pip install
        ]
        
        with patch('src.updates.console'):
            with patch('src.updates.Live'):
                result = update_app()
        
        assert result is True
        # Verify pip install was called
        pip_calls = [c for c in mock_run.call_args_list if 'pip' in str(c)]
        assert len(pip_calls) >= 1
