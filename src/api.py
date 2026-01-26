"""
Synchronous API client for incode-cli.

This module provides a synchronous wrapper around the asynchronous API client,
allowing the existing synchronous UI code to use async I/O for better performance
(parallel network requests) without requiring async/await throughout the codebase.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.api_async import AsyncIncodeRequests
from src.models import Duty

logger = logging.getLogger(__name__)


class IncodeRequests:
    """
    Synchronous facade for AsyncIncodeRequests.
    
    This class allows existing synchronous UI code to benefit from async I/O
    (parallel fetching) without rewriting the entire application logic.
    It manages an event loop and delegates all operations to the async client.
    
    Attributes:
        loop: The asyncio event loop used for running async operations.
        client: The underlying AsyncIncodeRequests instance.
        
    Example:
        >>> api = IncodeRequests("https://dienstplan.example.com")
        >>> api.login("username", "password")
        True
        >>> duties = api.load_future_duties()
        >>> print(len(duties))
        15
    """
    
    def __init__(self, base_url: str, extra_guids: Optional[List[str]] = None, username: Optional[str] = None) -> None:
        """
        Initialize the synchronous API client.
        
        Args:
            base_url: Base URL of the Incode system.
            extra_guids: Optional list of additional organization unit GUIDs.
            username: Optional username for cache key differentiation.
        """
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.client = AsyncIncodeRequests(base_url, extra_guids, username)
        
    def __del__(self) -> None:
        """Clean up the event loop and close the session."""
        try:
            if not self.loop.is_closed():
                self.loop.run_until_complete(self.client.close())
                self.loop.close()
        except (RuntimeError, AttributeError) as e:
            # Silently ignore cleanup errors during garbage collection
            logger.debug(f"Cleanup error (expected during shutdown): {e}")

    @property
    def discovered_name(self) -> Optional[str]:
        """The user's display name discovered during login."""
        return self.client.discovered_name

    @property
    def org_unit_data_guid(self) -> Optional[str]:
        """The primary organization unit GUID."""
        return self.client.org_unit_data_guid

    @property
    def username(self) -> Optional[str]:
        """The current username."""
        return self.client.username

    @property
    def base_url(self) -> str:
        """The base URL of the Incode system."""
        return self.client.base_url

    @property
    def header_key(self) -> Optional[str]:
        """The API authentication header key."""
        return self.client.header_key

    @property
    def header_value(self) -> Optional[str]:
        """The API authentication header value (token)."""
        return self.client.header_value

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with the Incode system.
        
        Args:
            username: The user's login name (personnel number).
            password: The user's password.
            
        Returns:
            True if login was successful.
            
        Raises:
            LoginError: If authentication fails.
        """
        return self.loop.run_until_complete(self.client.login(username, password))

    def get_project_guids(self) -> Dict[str, str]:
        """
        Retrieve available project GUIDs.
        
        Returns:
            Dictionary mapping project GUIDs to project names.
        """
        return self.loop.run_until_complete(self.client.get_project_guids())

    def load_events_plan(self) -> List[Dict[str, Any]]:
        """
        Load upcoming events/special duties.
        
        Returns:
            List of event dictionaries with details.
        """
        return self.loop.run_until_complete(self.client.load_events_plan())

    def load_future_duties(self, use_cache: bool = True, filter_mode: str = 'exclude_absences', override_name: Optional[str] = None) -> List[Duty]:
        """
        Load future duties for the current user.
        
        Args:
            use_cache: Whether to use cached data if available.
            filter_mode: 'exclude_absences', 'only_absences', or 'include_all'.
            override_name: Override name for crew reordering.
            
        Returns:
            List of Duty objects.
        """
        return self.loop.run_until_complete(self.client.load_future_duties(use_cache, filter_mode, override_name))

    def get_next_duty(self) -> Optional[Duty]:
        """
        Get the next upcoming duty.
        
        Returns:
            The next Duty object, or None if no upcoming duties.
        """
        return self.loop.run_until_complete(self.client.get_next_duty())

    def load_absences(self) -> List[Dict[str, Any]]:
        """
        Load absences (vacation, sick leave, etc.) for the current user.
        
        Returns:
            List of absence dictionaries.
        """
        return self.loop.run_until_complete(self.client.load_absences())
    
    def search_staff_contact(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for staff members by name, email, or phone.
        
        Args:
            query: Search query string.
            
        Returns:
            List of matching staff dictionaries.
        """
        return self.loop.run_until_complete(self.client.search_staff_contact(query))

    def load_daily_plan(self, date: datetime, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Load the daily duty plan for a specific date.
        
        Args:
            date: The date to load the plan for.
            use_cache: Whether to use cached data if available.
            
        Returns:
            List of shift dictionaries with crew and vehicle info.
        """
        return self.loop.run_until_complete(self.client.load_daily_plan(date, use_cache))

    def load_my_event_duties(self) -> List[Duty]:
        """
        Load event-related duties for the current user.
        
        Returns:
            List of Duty objects for events.
        """
        return self.loop.run_until_complete(self.client.load_my_event_duties())

    def load_archive_duties(self, year: int, filter_mode: str = 'exclude_absences') -> List[Duty]:
        """
        Load archived duties for a specific year.
        
        Args:
            year: The year to load duties from.
            filter_mode: 'exclude_absences', 'only_absences', or 'include_all'.
            
        Returns:
            List of Duty objects from the archive.
        """
        return self.loop.run_until_complete(self.client.load_archive_duties(year, filter_mode))

    def get_user_name(self, pnr: str) -> Optional[str]:
        """
        Look up a user's display name by personnel number.
        
        Args:
            pnr: Personnel number (Personalnummer).
            
        Returns:
            The user's display name, or None if not found.
        """
        try:
            results = self.search_staff_contact(pnr)
            for res in results:
                if str(res.get('personalnummer', '')) == str(pnr):
                    return str(res.get('_display_name', ''))
            
            for res in results:
                 if str(pnr) in str(res.get('personalnummer', '')):
                     return str(res.get('_display_name', ''))
            
            if self.discovered_name: 
                return self.discovered_name
            return None
        except Exception as e:
            logger.debug(f"get_user_name error: {e}")
            if self.discovered_name: 
                return self.discovered_name
            return None