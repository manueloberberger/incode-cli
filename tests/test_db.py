"""
Tests for the DatabaseManager class in src/db.py
"""
import pytest
import os
import sys
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to override DB_FILE before importing db module
import src.db as db_module


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_incode.db")
    
    # Backup original and set new path
    original_db_file = db_module.DB_FILE
    db_module.DB_FILE = temp_db_path
    
    # Reset singleton to force re-initialization
    db_module.DatabaseManager._instance = None
    db_module.DatabaseManager._initialized = False
    
    # Create fresh instance
    db = db_module.DatabaseManager()
    
    yield db
    
    # Cleanup
    db_module.DB_FILE = original_db_file
    db_module.DatabaseManager._instance = None
    db_module.DatabaseManager._initialized = False
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestUserManagement:
    """Tests for user CRUD operations."""
    
    def test_upsert_and_get_user(self, temp_db):
        """Test creating and retrieving a user."""
        temp_db.upsert_user(
            username="testuser",
            password="testpass",
            base_url="https://example.com",
            extra_guids=["guid1", "guid2"],
            real_name="Test User"
        )
        
        user = temp_db.get_user("testuser")
        
        assert user is not None
        assert user['username'] == "testuser"
        assert user['password'] == "testpass"
        assert user['base_url'] == "https://example.com"
        assert user['extra_guids'] == ["guid1", "guid2"]
        assert user['real_name'] == "Test User"

    def test_get_nonexistent_user(self, temp_db):
        """Test retrieving a user that doesn't exist."""
        user = temp_db.get_user("nonexistent")
        assert user is None

    def test_get_users_empty(self, temp_db):
        """Test retrieving users when none exist."""
        users = temp_db.get_users()
        assert users == []

    def test_get_users_multiple(self, temp_db):
        """Test retrieving multiple users."""
        temp_db.upsert_user("user1", "pass1", "https://a.com", [])
        temp_db.upsert_user("user2", "pass2", "https://b.com", [])
        
        users = temp_db.get_users()
        
        assert len(users) == 2
        usernames = [u['username'] for u in users]
        assert "user1" in usernames
        assert "user2" in usernames

    def test_update_existing_user(self, temp_db):
        """Test updating an existing user."""
        temp_db.upsert_user("testuser", "oldpass", "https://old.com", [])
        temp_db.upsert_user("testuser", "newpass", "https://new.com", ["guid"])
        
        user = temp_db.get_user("testuser")
        
        assert user['password'] == "newpass"
        assert user['base_url'] == "https://new.com"
        assert user['extra_guids'] == ["guid"]

    def test_remove_user(self, temp_db):
        """Test removing a user."""
        temp_db.upsert_user("testuser", "pass", "https://x.com", [])
        
        # Verify exists
        assert temp_db.get_user("testuser") is not None
        
        temp_db.remove_user("testuser")
        
        # Verify removed
        assert temp_db.get_user("testuser") is None

    def test_active_user(self, temp_db):
        """Test setting and getting active user."""
        temp_db.upsert_user("user1", "pass", "https://x.com", [])
        temp_db.upsert_user("user2", "pass", "https://x.com", [])
        
        temp_db.set_active_user("user1")
        assert temp_db.get_active_user() == "user1"
        
        temp_db.set_active_user("user2")
        assert temp_db.get_active_user() == "user2"


class TestValueStore:
    """Tests for key-value store operations."""
    
    def test_set_and_get_value(self, temp_db):
        """Test setting and getting a value."""
        temp_db.set_value("test_key", "test_value")
        
        result = temp_db.get_value("test_key")
        
        assert result == "test_value"

    def test_get_value_default(self, temp_db):
        """Test getting a nonexistent key returns default."""
        result = temp_db.get_value("nonexistent", "default")
        assert result == "default"

    def test_set_value_complex(self, temp_db):
        """Test storing complex types (dict, list)."""
        temp_db.set_value("dict_key", {"a": 1, "b": [1, 2, 3]})
        temp_db.set_value("list_key", [1, 2, 3])
        temp_db.set_value("int_key", 42)
        
        assert temp_db.get_value("dict_key") == {"a": 1, "b": [1, 2, 3]}
        assert temp_db.get_value("list_key") == [1, 2, 3]
        assert temp_db.get_value("int_key") == 42

    def test_update_value(self, temp_db):
        """Test updating an existing value."""
        temp_db.set_value("key", "old")
        temp_db.set_value("key", "new")
        
        assert temp_db.get_value("key") == "new"


class TestCache:
    """Tests for cache operations."""
    
    def test_set_and_get_cache(self, temp_db):
        """Test basic cache set/get."""
        temp_db.set_cache("cache_key", {"data": "test"})
        
        result = temp_db.get_cache("cache_key", ttl=3600)
        
        assert result == {"data": "test"}

    def test_cache_expiration(self, temp_db):
        """Test cache expiration with TTL=0."""
        import time
        temp_db.set_cache("expire_key", "value")
        time.sleep(0.1)
        
        # TTL of 0 should always be expired
        result = temp_db.get_cache("expire_key", ttl=0)
        
        assert result is None

    def test_cache_not_expired(self, temp_db):
        """Test cache not expired within TTL."""
        temp_db.set_cache("valid_key", "value")
        
        # Large TTL should not expire
        result = temp_db.get_cache("valid_key", ttl=3600)
        
        assert result == "value"

    def test_cache_nonexistent(self, temp_db):
        """Test getting nonexistent cache key."""
        result = temp_db.get_cache("nonexistent", ttl=3600)
        assert result is None
