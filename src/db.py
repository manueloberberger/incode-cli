import sqlite3
import json
import os
import time
from typing import Any, Dict, List, Optional, cast
from threading import Lock

DB_FILE = "incode.db"

class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _lock = Lock()
    _initialized: bool = False

    def __new__(cls) -> 'DatabaseManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized: return
        self._initialized = True
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

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
                is_active INTEGER DEFAULT 0
            )
        """)
        
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
        
        conn.commit()
        conn.close()

    # --- User Management ---

    def get_users(self) -> List[Dict[str, Any]]:
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
                except:
                    u['extra_guids'] = []
            users.append(u)
        conn.close()
        return users

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            u = dict(row)
            if u['extra_guids']:
                try:
                    u['extra_guids'] = json.loads(u['extra_guids'])
                except:
                    u['extra_guids'] = []
            return u
        return None

    def upsert_user(self, username: str, password: str, base_url: str, extra_guids: List[str], real_name: Optional[str] = None) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password, base_url, extra_guids, real_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password=excluded.password,
                base_url=excluded.base_url,
                extra_guids=excluded.extra_guids,
                real_name=excluded.real_name
        """, (username, password, base_url, json.dumps(extra_guids), real_name))
        conn.commit()
        conn.close()

    def remove_user(self, username: str) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        conn.close()

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
        conn.close()
        if row:
            try:
                return json.loads(row['value'])
            except:
                return row['value']
        return default

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
        conn.close()

    # --- Cache ---

    def get_cache(self, key: str, ttl: int) -> Optional[Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value, timestamp FROM cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            ts = row['timestamp']
            if time.time() - ts < ttl:
                try:
                    return json.loads(row['value'])
                except:
                    return None
            else:
                # Cleanup old cache immediately? Or lazy?
                # For now, just return None
                pass
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
        conn.close()



db = DatabaseManager()
