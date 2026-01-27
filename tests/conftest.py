import sys
import os
import pytest

# Ensure 'src' is importable by adding the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(autouse=True)
def reset_db_singleton():
    """Reset the DatabaseManager singleton after each test to ensure test isolation."""
    yield
    # Cleanup after test
    from src.db import DatabaseManager
    DatabaseManager.reset_instance()
