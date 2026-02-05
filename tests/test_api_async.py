"""
Tests for the async API client module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import aiohttp

from src.api_async import AsyncIncodeRequests
from src.exceptions import LoginError, ApiError


class TestAsyncIncodeRequestsInit:
    """Tests for AsyncIncodeRequests initialization."""
    
    def test_init_with_defaults(self):
        """Should initialize with default values."""
        client = AsyncIncodeRequests("https://example.com")
        assert client.base_url == "https://example.com"
        assert client.extra_guids == []
        assert client.username is None
        assert client.session is None
    
    def test_init_with_extra_guids(self):
        """Should initialize with extra GUIDs."""
        client = AsyncIncodeRequests("https://example.com", extra_guids=["guid1", "guid2"])
        assert client.extra_guids == ["guid1", "guid2"]
    
    def test_init_with_username(self):
        """Should initialize with username for cache keys."""
        client = AsyncIncodeRequests("https://example.com", username="testuser")
        assert client.username == "testuser"


class TestCacheKeyGeneration:
    """Tests for cache key generation."""
    
    def test_cache_key_with_username(self):
        """Should prefix cache key with username."""
        client = AsyncIncodeRequests("https://example.com", username="user123")
        key = client._get_cache_key("duties")
        assert key == "user123_duties"
    
    def test_cache_key_without_username(self):
        """Should return raw key when no username."""
        client = AsyncIncodeRequests("https://example.com")
        key = client._get_cache_key("duties")
        assert key == "duties"


class TestApiHeaders:
    """Tests for API header generation."""
    
    def test_headers_without_auth(self):
        """Should return basic headers when not authenticated."""
        client = AsyncIncodeRequests("https://example.com")
        headers = client._get_api_headers()
        assert 'Accept' in headers
        assert 'X-Requested-With' in headers
    
    def test_headers_with_auth(self):
        """Should include auth token in headers when authenticated."""
        client = AsyncIncodeRequests("https://example.com")
        client.header_key = "x-incode-token"
        client.header_value = "secret123"
        headers = client._get_api_headers()
        assert headers["x-incode-token"] == "secret123"


class TestEnsureSession:
    """Tests for session management."""
    
    @pytest.mark.asyncio
    async def test_ensure_session_creates_new(self):
        """Should create a new session if none exists."""
        client = AsyncIncodeRequests("https://example.com")
        assert client.session is None
        await client.ensure_session()
        assert client.session is not None
        await client.close()
    
    @pytest.mark.asyncio
    async def test_ensure_session_reuses_existing(self):
        """Should not recreate session if one exists."""
        client = AsyncIncodeRequests("https://example.com")
        await client.ensure_session()
        session1 = client.session
        await client.ensure_session()
        assert client.session is session1
        await client.close()


class TestClose:
    """Tests for session cleanup."""
    
    @pytest.mark.asyncio
    async def test_close_cleans_session(self):
        """Should close and clear session."""
        client = AsyncIncodeRequests("https://example.com")
        await client.ensure_session()
        assert client.session is not None
        await client.close()
        assert client.session is None


class TestContextManager:
    """Tests for async context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Should work as async context manager."""
        async with AsyncIncodeRequests("https://example.com") as client:
            assert client.session is not None
        # Session should be closed after exiting context
        assert client.session is None


class TestLogin:
    """Tests for login functionality."""
    
    @pytest.mark.asyncio
    async def test_login_missing_session_id(self):
        """Should raise LoginError if no session ID returned."""
        with patch.object(AsyncIncodeRequests, 'ensure_session', new_callable=AsyncMock):
            client = AsyncIncodeRequests("https://example.com")
            client.session = MagicMock()
            client.session.cookie_jar = MagicMock()
            client.session.cookie_jar.filter_cookies = MagicMock(return_value={})
            
            mock_response = AsyncMock()
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            client.session.post = MagicMock(return_value=mock_response)
            
            with pytest.raises(LoginError, match="Session-ID"):
                await client.login("user", "pass")
            
            # Clean up - set session to None to avoid async close issues
            client.session = None
    
    @pytest.mark.asyncio
    async def test_login_extracts_tokens(self):
        """Should extract auth tokens from response."""
        with patch.object(AsyncIncodeRequests, 'ensure_session', new_callable=AsyncMock):
            client = AsyncIncodeRequests("https://example.com")
            client.session = MagicMock()
            
            # Mock cookie jar with PHPSESSID
            mock_cookies = {'PHPSESSID': 'abc123'}
            client.session.cookie_jar = MagicMock()
            client.session.cookie_jar.filter_cookies = MagicMock(return_value=mock_cookies)
            
            # Mock responses
            html_content = """
            'x-incode-abcdef': 'token12345',
            'orgUnitDataGuid': 'guid_abc_123',
            'user_name': 'Max Mustermann'
            """
            
            mock_post_response = AsyncMock()
            mock_post_response.__aenter__.return_value = mock_post_response
            mock_post_response.__aexit__.return_value = None
            
            mock_get_response = AsyncMock()
            mock_get_response.__aenter__.return_value = mock_get_response
            mock_get_response.__aexit__.return_value = None
            mock_get_response.text = AsyncMock(return_value=html_content)
            
            client.session.post = MagicMock(return_value=mock_post_response)
            client.session.get = MagicMock(return_value=mock_get_response)
            
            result = await client.login("user", "pass")
            
            assert result is True
            assert client.header_key == "x-incode-abcdef"
            assert client.header_value == "token12345"
            assert client.discovered_name == "Max Mustermann"
            
            # Clean up - set session to None to avoid async close issues
            client.session = None


class TestGetNextDuty:
    """Tests for get_next_duty functionality."""
    
    @pytest.mark.asyncio
    async def test_get_next_duty_empty(self):
        """Should return None when no future duties."""
        with patch.object(AsyncIncodeRequests, 'load_future_duties', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = []
            
            client = AsyncIncodeRequests("https://example.com")
            result = await client.get_next_duty()
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_next_duty_finds_future(self):
        """Should return next upcoming duty."""
        from src.models import Duty
        
        future_time = datetime.now() + timedelta(days=1)
        past_time = datetime.now() - timedelta(days=1)
        
        duties = [
            Duty(begin=past_time, end=past_time + timedelta(hours=8), vehicle="RTW 1", location="Station", duty_type="Ehrenamt", crew={}),
            Duty(begin=future_time, end=future_time + timedelta(hours=8), vehicle="RTW 2", location="Station", duty_type="Ehrenamt", crew={})
        ]
        
        with patch.object(AsyncIncodeRequests, 'load_future_duties', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = duties
            
            client = AsyncIncodeRequests("https://example.com")
            result = await client.get_next_duty()
            
            assert result is not None
            assert result.vehicle == "RTW 2"


class TestCaching:
    """Tests for caching functionality."""
    
    def test_set_and_get_cached_data(self):
        """Should store and retrieve cached data."""
        with patch('src.api_async.db') as mock_db:
            mock_db.set_cache = MagicMock()
            mock_db.get_cache = MagicMock(return_value={'test': 'data'})
            
            client = AsyncIncodeRequests("https://example.com", username="user1")
            
            # Set cache
            client._set_cached_data("key1", {'test': 'data'})
            mock_db.set_cache.assert_called_once_with("user1_key1", {'test': 'data'})
            
            # Get cache
            result = client._get_cached_data("key1")
            assert result == {'test': 'data'}
