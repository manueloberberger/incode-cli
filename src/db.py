"""
Database abstraction layer for incode-cli.

Manages the local SQLite database (`incode.db`) which stores:
- User credentials and configuration
- Application settings (Key-Value store)
- API response cache
"""
import atexit
import sqlite3
import json
import logging
import time
from typing import Any, Dict, List, Optional
from threading import Lock

logger = logging.getLogger(__name__)


def _cleanup_db_connection() -> None:
    """Cleanup function to close database connection on exit."""
    if DatabaseManager._instance is not None:
        DatabaseManager._instance.close()


atexit.register(_cleanup_db_connection)

DB_FILE = "incode.db"

class DatabaseManager:
    """
    Singleton class managing SQLite database connections and operations.

    Thread-safe implementation using a lock for instance creation.
    Provides methods for user management, key-value storage, and caching.
    Uses connection pooling for improved performance.
    """
    _instance: Optional['DatabaseManager'] = None
    _lock = Lock()
    _initialized: bool = False
    _connection: Optional[sqlite3.Connection] = None
    _conn_lock: Lock

    def __new__(cls) -> 'DatabaseManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
                cls._instance._conn_lock = Lock()
            return cls._instance

    def __init__(self) -> None:
        if self._initialized: return
        self._initialized = True
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a cached connection or creates a new one (connection pooling)."""
        with self._conn_lock:
            if self._connection is None:
                self._connection = sqlite3.connect(DB_FILE, check_same_thread=False)
                self._connection.row_factory = sqlite3.Row
            return self._connection

    def close(self) -> None:
        """Close the cached database connection."""
        with self._conn_lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing purposes)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

    def _init_db(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # User Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                base_url TEXT,
                extra_guids TEXT,
                real_name TEXT,
                is_active INTEGER DEFAULT 0,
                telegram_token TEXT,
                allowed_user_id INTEGER
            )
        """)

        # Migration: Add columns if they don't exist (for existing users tables)
        try:
            cursor.execute("SELECT telegram_token FROM users LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN telegram_token TEXT")
                cursor.execute("ALTER TABLE users ADD COLUMN allowed_user_id INTEGER")
                conn.commit()
            except Exception as e:
                logger.warning(f"Database migration error: {e}")

        
        # Key-Value Store (Settings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS valuestore (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Cache Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                timestamp REAL
            )
        """)

        # Performance indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON cache(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")

        conn.commit()

        # Clean up expired cache entries on startup
        self.clear_expired_cache()

    # --- User Management ---

    def get_users(self) -> List[Dict[str, Any]]:
        """
        Retrieve all configured users.
        
        Returns:
            List of dictionaries containing user data (username, password, settings).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        users = []
        for row in rows:
            u = dict(row)
            if u['extra_guids']:
                try:
                    u['extra_guids'] = json.loads(u['extra_guids'])
                except (json.JSONDecodeError, TypeError):
                    u['extra_guids'] = []
            users.append(u)
        return users

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific user by username.
        
        Args:
            username: The username to search for.
            
        Returns:
            User dictionary if found, None otherwise.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            u = dict(row)
            if u['extra_guids']:
                try:
                    u['extra_guids'] = json.loads(u['extra_guids'])
                except (json.JSONDecodeError, TypeError):
                    u['extra_guids'] = []
            return u
        return None

    def upsert_user(self, username: str, password: str, base_url: str, extra_guids: List[str], real_name: Optional[str] = None, telegram_token: Optional[str] = None, allowed_user_id: Optional[int] = None) -> None:
        """
        Insert or Update a user record.
        
        Args:
            username: The user's login name (Primary Key).
            password: Login password.
            base_url: API base URL.
            extra_guids: List of additional unit GUIDs.
            real_name: Display name/alias for the user.
            telegram_token: Token for Telegram bot integration.
            allowed_user_id: Telegram user ID allowed to access bot.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password, base_url, extra_guids, real_name, telegram_token, allowed_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password=excluded.password,
                base_url=excluded.base_url,
                extra_guids=excluded.extra_guids,
                real_name=excluded.real_name,
                telegram_token=excluded.telegram_token,
                allowed_user_id=excluded.allowed_user_id
        """, (username, password, base_url, json.dumps(extra_guids), real_name, telegram_token, allowed_user_id))
        conn.commit()

    def remove_user(self, username: str) -> None:
        """
        Delete a user record.
        
        Args:
            username: The username to delete.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()

    def set_active_user(self, username: str) -> None:
        # We store 'last_active' in valuestore instead of a flag in users table 
        # to avoid complex update logic (resetting others)
        self.set_value("last_active_user", username)

    def get_active_user(self) -> Optional[str]:
        val = self.get_value("last_active_user")
        if val is None: return None
        return str(val)

    # --- Value Store ---

    def get_value(self, key: str, default: Any = None) -> Any:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM valuestore WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row['value'])
            except (json.JSONDecodeError, TypeError):
                return row['value']
        return default

    def get_all_values(self) -> Dict[str, Any]:
        """Returns all key-value pairs from the valuestore."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM valuestore")
        rows = cursor.fetchall()
        result = {}
        for row in rows:
            key = row['key']
            try:
                result[key] = json.loads(row['value'])
            except (json.JSONDecodeError, TypeError):
                result[key] = row['value']
        return result

    def set_value(self, key: str, value: Any) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        val_str = json.dumps(value)
        cursor.execute("""
            INSERT INTO valuestore (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, val_str))
        conn.commit()

    # --- Cache ---

    def get_cache(self, key: str, ttl: int) -> Optional[Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value, timestamp FROM cache WHERE key = ?", (key,))
        row = cursor.fetchone()

        if row:
            ts = row['timestamp']
            if time.time() - ts < ttl:
                try:
                    return json.loads(row['value'])
                except (json.JSONDecodeError, TypeError):
                    return None
            else:
                # Remove expired entry immediately
                cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
        return None

    def set_cache(self, key: str, value: Any) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        val_str = json.dumps(value)
        cursor.execute("""
            INSERT INTO cache (key, value, timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, timestamp=excluded.timestamp
        """, (key, val_str, time.time()))
        conn.commit()

    def clear_expired_cache(self, ttl: int = 900) -> int:
        """
        Remove all expired cache entries.

        Args:
            ttl: Time-to-live in seconds (default: 900 = 15 minutes).

        Returns:
            Number of deleted entries.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cutoff = time.time() - ttl
        cursor.execute("DELETE FROM cache WHERE timestamp < ?", (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted



db = DatabaseManager()
