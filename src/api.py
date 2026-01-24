import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from src.api_async import AsyncIncodeRequests
from src.models import Duty
from src.exceptions import LoginError, ApiError
from src.utils import handle_api_errors

logger = logging.getLogger(__name__)

class IncodeRequests:
    """
    Synchronous Facade for AsyncIncodeRequests.
    Allows existing synchronous UI code to benefit from Async I/O (parallel fetching)
    without rewriting the entire application logic.
    """
    def __init__(self, base_url: str, extra_guids: Optional[List[str]] = None, username: Optional[str] = None) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.client = AsyncIncodeRequests(base_url, extra_guids, username)
        
    def __del__(self):
        try:
            if not self.loop.is_closed():
                self.loop.run_until_complete(self.client.close())
                self.loop.close()
        except: pass

    @property
    def discovered_name(self) -> Optional[str]:
        return self.client.discovered_name

    @property
    def org_unit_data_guid(self) -> Optional[str]:
        return self.client.org_unit_data_guid

    @property
    def username(self) -> Optional[str]:
        return self.client.username

    @property
    def base_url(self) -> str:
        return self.client.base_url

    @property
    def header_key(self) -> Optional[str]:
        return self.client.header_key

    @property
    def header_value(self) -> Optional[str]:
        return self.client.header_value

    def login(self, username: str, password: str) -> bool:
        return self.loop.run_until_complete(self.client.login(username, password))

    def get_project_guids(self) -> Dict[str, str]:
        return self.loop.run_until_complete(self.client.get_project_guids())

    def load_events_plan(self) -> List[Dict[str, Any]]:
        return self.loop.run_until_complete(self.client.load_events_plan())

    def load_future_duties(self, use_cache: bool = True, filter_mode: str = 'exclude_absences', override_name: Optional[str] = None) -> List[Duty]:
        return self.loop.run_until_complete(self.client.load_future_duties(use_cache, filter_mode, override_name))

    def get_next_duty(self) -> Optional[Duty]:
        return self.loop.run_until_complete(self.client.get_next_duty())

    def load_absences(self) -> List[Dict[str, Any]]:
        return self.loop.run_until_complete(self.client.load_absences())
    
    def search_staff_contact(self, query: str) -> List[Dict[str, Any]]:
        return self.loop.run_until_complete(self.client.search_staff_contact(query))

    def load_daily_plan(self, date: datetime, use_cache: bool = True) -> List[Dict[str, Any]]:
        return self.loop.run_until_complete(self.client.load_daily_plan(date, use_cache))

    def load_my_event_duties(self) -> List[Duty]:
        return self.loop.run_until_complete(self.client.load_my_event_duties())

    def load_archive_duties(self, year: int, filter_mode: str = 'exclude_absences') -> List[Duty]:
        return self.loop.run_until_complete(self.client.load_archive_duties(year, filter_mode))

    def get_user_name(self, pnr: str) -> Optional[str]:
        try:
            results = self.search_staff_contact(pnr)
            for res in results:
                if str(res.get('personalnummer', '')) == str(pnr):
                    return str(res.get('_display_name', ''))
            
            for res in results:
                 if str(pnr) in str(res.get('personalnummer', '')):
                     return str(res.get('_display_name', ''))
            
            if self.discovered_name: return self.discovered_name
            return None
        except Exception as e:
            logger.debug(f"get_user_name error: {e}")
            if self.discovered_name: return self.discovered_name
            return None