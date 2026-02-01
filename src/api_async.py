"""
Asynchronous API client for incode-cli.

This module provides the core async API client for communicating with the
Incode duty roster system. It handles authentication, session management,
and all API requests using aiohttp for efficient parallel network operations.

The AsyncIncodeRequests class supports:
- Login and authentication token management
- Loading duties, absences, and events
- Staff directory search
- Daily plan retrieval
- Caching for improved performance
"""
import sys
try:
    import aiohttp
except ImportError:
    print(f"CRITICAL ERROR: 'aiohttp' not found.")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Path: {sys.path}")
    print("Please run: python3 -m pip install aiohttp --break-system-packages")
    sys.exit(1)
import asyncio
import re
import logging
from datetime import datetime, timedelta, date
from yarl import URL
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any, cast

from src.db import db
from src.exceptions import LoginError, ApiError
from src.utils import get_holidays
from src.parser import (
    fix_datetime,
    parse_staff_contact,
    parse_personal_duties,
    parse_daily_plan_raw
)

from src.models import Duty

logger = logging.getLogger(__name__)

CACHE_TTL = 900

class AsyncIncodeRequests:
    """
    Asynchronous API client for the Incode duty roster system.
    
    This class handles all communication with the Incode API using aiohttp
    for efficient async I/O. It supports parallel fetching of data from
    multiple organizational units.
    
    Attributes:
        base_url: The base URL of the Incode system.
        extra_guids: Additional organization unit GUIDs to query.
        username: Current user's username for cache differentiation.
        session: The aiohttp ClientSession for making requests.
        header_key: API authentication header name.
        header_value: API authentication token.
        org_unit_data_guid: Primary organization unit GUID.
        discovered_name: User's display name discovered during login.
        
    Example:
        >>> async with AsyncIncodeRequests("https://example.com") as api:
        ...     await api.login("user", "pass")
        ...     duties = await api.load_future_duties()
    """
    
    def __init__(self, base_url: str, extra_guids: Optional[List[str]] = None, username: Optional[str] = None) -> None:
        """
        Initialize the async API client.
        
        Args:
            base_url: Base URL of the Incode system.
            extra_guids: Optional list of additional organization unit GUIDs.
            username: Optional username for cache key differentiation.
        """
        self.base_url = base_url
        self.extra_guids = extra_guids if extra_guids else []
        self.username = username
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15'
        self.session: Optional[aiohttp.ClientSession] = None
        self.header_key: Optional[str] = None
        self.header_value: Optional[str] = None
        self.org_unit_data_guid: Optional[str] = None
        self.discovered_name: Optional[str] = None

    async def __aenter__(self) -> "AsyncIncodeRequests":
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the aiohttp session and clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

    async def ensure_session(self) -> None:
        """Ensure an aiohttp session exists, creating one if necessary."""
        if not self.session:
             self.session = aiohttp.ClientSession(headers={'User-Agent': self.user_agent})

    def _get_cache_key(self, key_base: str) -> str:
        """Generate a user-specific cache key."""
        if self.username:
            return f"{self.username}_{key_base}"
        return key_base

    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Retrieve data from cache if not expired."""
        key = self._get_cache_key(key)
        return db.get_cache(key, CACHE_TTL)

    def _set_cached_data(self, key: str, data: Any) -> None:
        """Store data in cache with current timestamp."""
        key = self._get_cache_key(key)
        db.set_cache(key, data)

    def _get_api_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API requests including auth token."""
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest'}
        if self.header_key and self.header_value: headers[self.header_key] = self.header_value
        return headers

    async def login(self, username: str, password: str) -> bool:
        """
        Authenticate with the Incode system.
        
        Performs login, extracts auth tokens from response, and discovers
        available organization unit GUIDs.
        
        Args:
            username: The user's login name (personnel number).
            password: The user's password.
            
        Returns:
            True if login was successful.
            
        Raises:
            LoginError: If authentication fails or tokens cannot be extracted.
        """
        await self.ensure_session()
        login_url = f"{self.base_url}/login.php"
        login_body = {'client': 'dienstplan', 'login': username, 'password': password}
        
        try:
            if not self.session: raise LoginError("Session initialization failed")
            async with self.session.post(login_url, data=login_body) as resp:
                # Check cookies
                cookies = self.session.cookie_jar.filter_cookies(URL(self.base_url))
                if 'PHPSESSID' not in cookies:
                     raise LoginError("Login fehlgeschlagen (Keine Session-ID)")

            if not self.session: raise LoginError("Session lost")
            async with self.session.get(f"{self.base_url}/") as resp:
                content = await resp.text()

            # Parse API authentication headers from JavaScript config
            # Pattern matches: 'x-incode-xxx': 'token_value' or "x-incode-xxx": "token_value"
            # This extracts the custom auth header name and token from embedded JS
            inc_m = re.search(r'''['"](x-incode-[^'" ]+)['"]\s*:\s*['"]([^'" ]+)['"]''', content)
            if inc_m: self.header_key, self.header_value = inc_m.group(1), inc_m.group(2)

            # Extract organization unit GUIDs from JavaScript config
            # Pattern matches: "orgUnitDataGuid": "hash_value" or 'orgUnitDataGuid': 'hash_value'
            # GUIDs identify which organizational units the user has access to
            guids = re.findall(r'''["']orgUnitDataGuid["']\s*:\s*["']([^"]+)["']''', content)
            
            if not guids:
                # Fallback to dispo.php if not found on main page
                if not self.session: raise LoginError("Session lost")
                async with self.session.get(f"{self.base_url}/StaffPortal/dispo.php") as disp_resp:
                    disp_text = await disp_resp.text()
                    guids = re.findall(r'''["']orgUnitDataGuid["']\s*:\s*["']([^"]+)["']''', disp_text)
                
            # Deduplicate preserving order
            discovered_guids = list(dict.fromkeys(guids))
            
            if discovered_guids:
                # Prefer the first one usually as it's the main context
                self.org_unit_data_guid = discovered_guids[0]
                self.extra_guids = discovered_guids

            if not self.header_key or not self.header_value:
                raise LoginError(
                    "Login fehlgeschlagen (Tokens nicht gefunden). "
                    "Bitte Zugangsdaten prüfen oder im Browser einloggen um den Account-Status zu verifizieren."
                )
            
            nm = re.search(r'''["']user_name["']\s*:\s*["']([^"']+)["']''', content)
            if nm: self.discovered_name = nm.group(1)
            
            return True

        except LoginError:
            raise
        except Exception as e:
            raise LoginError(f"Systemfehler beim Login: {e}") from e

    async def get_project_guids(self) -> Dict[str, Any]:
        """
        Retrieve available project/event GUIDs.

        Discovers project GUIDs from the projects page and maps them
        to their display names.

        Returns:
            Dictionary mapping project GUIDs to project names.
        """
        await self.ensure_session()
        if self.session is None:
            raise RuntimeError("Session initialization failed")
        project_map = {}
        try:
            async with self.session.get(f"{self.base_url}/StaffPortal/projects.php", headers=self._get_api_headers()) as r_proj:
                txt = await r_proj.text()
                
            # Pattern matches GUIDs: 40 hex chars followed by underscore-separated numbers
            # Example: "abc123...def456_1_2_3" - identifies projects/events
            guid_pattern = r'([a-f0-9]{40}(?:_\d+)+)'
            all_raw = set(re.findall(guid_pattern, txt))
            if self.org_unit_data_guid: all_raw.add(self.org_unit_data_guid)
            if self.extra_guids: all_raw.update(self.extra_guids)
            # Removed unused DEFAULT_GUID
            guids_to_try = list(all_raw)
            
            if not guids_to_try: return {}

            async with self.session.post(f"{self.base_url}/StaffPortal/projects/show.content.projects.php", headers=self._get_api_headers(), data={'orgUnitDataGuid[]': guids_to_try, 'projectType': '', 'name': '', 'month': '', 'form.event.onsubmit': 'searchForm'}) as resp:
                if resp.status == 200:
                    text_resp = await resp.text()
                    soup = BeautifulSoup(text_resp, 'html.parser')
                    for inp in soup.find_all('input', value=True):
                        val = inp['value']
                        if re.match(r'^[a-f0-9]{40}(?:_\d+)+$', val) and val not in guids_to_try:
                            name, row = "Event", inp.find_parent('tr')
                            if row:
                                txt = " ".join(row.get_text(separator=" ").split()).replace(val, "").strip()
                                if len(txt) > 3: name = txt
                            if name == "Event" and inp.get('id'):
                                lbl = soup.find('label', attrs={'for': inp.get('id')})
                                if lbl: name = lbl.get_text(strip=True)
                            project_map[val] = name
                    for g in re.findall(guid_pattern, text_resp):
                        if g not in project_map and g not in guids_to_try: project_map[g] = "Event"
        except aiohttp.ClientError as e:
            logger.debug(f"Network error fetching project GUIDs: {e}")
        except Exception as e:
            logger.debug(f"Error fetching project GUIDs: {e}")
        return project_map

    async def load_events_plan(self) -> List[Dict[str, Any]]:
        # pm = await self.get_project_guids() # Unused
        guids_to_try = [self.org_unit_data_guid] + self.extra_guids
        events = []
        
        try:
            if not self.session: await self.ensure_session()
            if self.session is None:
                raise RuntimeError("Session initialization failed")
            async with self.session.post(f"{self.base_url}/StaffPortal/projects/show.content.projects.php", headers=self._get_api_headers(), data={'orgUnitDataGuid[]': guids_to_try, 'projectType': '', 'name': '', 'month': '', 'form.event.onsubmit': 'searchForm'}) as resp:
                if resp.status == 200:
                    soup = BeautifulSoup(await resp.text(), 'html.parser')
                    for card in soup.find_all('div', attrs={'data-role': 'incode-project'}):
                        guid, b_s, e_s = card.get('data-dataguid'), card.get('data-begin'), card.get('data-end')
                        if not guid or not b_s: continue
                        b_dt, e_dt = fix_datetime(b_s), fix_datetime(e_s)
                        if not b_dt: continue
                        t_tag = card.find('h3', class_='card-title')
                        events.append({'guid': guid, 'begin': b_dt, 'end': e_dt, 'vehicle': t_tag.get_text(strip=True) if t_tag else "Event", 'location': '', 'crew': {}, 'open_slots': 0})
        except Exception as exc:
            logger.warning(f"Events load error: {exc}")
            return []

        if not events: return []

        start, end = min(e['begin'] for e in events), max(e['end'] for e in events)
        guids = list(set([e['guid'] for e in events]))
        main_org = self.org_unit_data_guid or (self.extra_guids[0] if self.extra_guids else "") or ""

        async def fetch_chunk(chunk_guids: List[str]) -> Optional[Dict[str, Any]]:
             try:
                 # asserted self.session
                 if not self.session: return None
                 async with self.session.post(f"{self.base_url}/StaffPortal/plan/data/loadProjectsPlan.json", headers=self._get_api_headers(), data={'orgUnitDataGuid': main_org, 'withSubOrgUnits': '1', 'sortPlan': 'false', 'dateFrom': start.strftime('%Y-%m-%dT00:00:00.000Z'), 'dateTo': end.strftime('%Y-%m-%dT23:59:59.000Z'), 'projectDataGuids[]': chunk_guids}) as r:
                     if r.status == 200:
                         return cast(Dict[str, Any], await r.json(content_type=None))
             except aiohttp.ClientError as e:
                logger.debug(f"Network error fetching event chunk: {e}")
             except Exception as e:
                logger.debug(f"Error fetching event chunk: {e}")
             return None

        # PARALLEL FETCHING
        tasks = []
        for i in range(0, len(guids), 30):
            tasks.append(fetch_chunk(guids[i:i+30]))
        
        results = await asyncio.gather(*tasks)
        
        # Build event index for O(1) lookups instead of O(n) nested loop
        event_map: Dict[tuple[str, date], Dict[str, Any]] = {}
        for e in events:
            key = (e['guid'], e['begin'].date())
            event_map[key] = e
        
        for data in results:
            if not data: continue
            it = data.get('data', {}).values() if isinstance(data.get('data'), dict) else data.get('data', [])
            for item in it:
                if not isinstance(item, dict): continue
                pg, cb = item.get('projectDataGuid'), fix_datetime(item.get('begin'))
                if not pg or not cb: continue
                
                # O(1) lookup instead of O(n) loop
                evt = event_map.get((pg, cb.date()))
                if evt:
                    infos = item.get('additionalInfos', {})
                    rn, pn, loc = str(infos.get('ressource_name', '')).strip(), str(infos.get('project_name', '')).strip(), str(item.get('orgUnitName', '')).strip()
                    if pn and (evt['vehicle'] == "Event" or len(pn) > len(evt['vehicle'])): evt['vehicle'] = pn
                    if loc: evt['location'] = loc
                    eid = str(item.get('externalId', '')).upper()
                    if not rn or rn == '*':
                        if eid != "KFZ": evt['open_slots'] += 1
                    elif eid != "KFZ": evt['crew'][f"{eid or 'Staff'}_{len(evt['crew'])}"] = rn
        return events

    async def load_archive_duties(self, year: int, filter_mode: str = 'exclude_absences') -> List[Duty]:
        """
        Load archived duties from a specific year.
        
        Args:
            year: The year to load duties from.
            filter_mode: 'exclude_absences', 'only_absences', or 'include_all'.
            
        Returns:
            List of Duty objects from the archive.
        """
        try:
            if not self.session: await self.ensure_session()
            if self.session is None:
                raise RuntimeError("Session initialization failed")
            async with self.session.post(f"{self.base_url}/StaffPortal/archive/data/loadDuties.json", headers=self._get_api_headers(), data={'year': str(year), 'month': '', 'dateDescendingSort': 'true', 'orgUnit': '', 'withSubOrgs': 'on', 'form.event.onsubmit': 'searchForm'}) as resp:
                if resp.status == 200:
                    return parse_personal_duties(await resp.json(content_type=None), filter_mode)
        except aiohttp.ClientError as e:
            logger.debug(f"Network error loading archive duties: {e}")
        except Exception as e:
            logger.debug(f"Error loading archive duties: {e}")
        return []

    async def load_future_duties(self, use_cache: bool = True, filter_mode: str = 'exclude_absences', override_name: Optional[str] = None) -> List[Duty]:
        """
        Load future duties for the current user.
        
        Fetches duties from both the main duties endpoint and the archive,
        merging results and applying caching for performance.
        
        Args:
            use_cache: Whether to use cached data if available.
            filter_mode: 'exclude_absences', 'only_absences', or 'include_all'.
            override_name: Override name for crew list reordering.
            
        Returns:
            List of Duty objects sorted by begin date.
        """
        cache_key = f"future_duties_{filter_mode}"
        if use_cache:
            cd = self._get_cached_data(cache_key)
            if cd:
                 # Serialization hydration
                 return [Duty(
                    begin=datetime.strptime(d['begin'], '%Y-%m-%dT%H:%M:%S'),
                    end=datetime.strptime(d['end'], '%Y-%m-%dT%H:%M:%S'),
                    vehicle=d['vehicle'],
                    location=d['location'],
                    duty_type=d['duty_type'],
                    crew=d['crew'],
                    comment=d.get('comment')
                ) for d in cd]

        await self.ensure_session()
        now = datetime.now()
        start_fetch = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        # Load ~6 months into future
        nm_end = (now + timedelta(days=180)).replace(hour=23, minute=59, second=59)
        ts_s, ts_e = int(start_fetch.timestamp()), int(nm_end.timestamp())
        
        data = {'max': '2000', 'dateFrom': start_fetch.strftime('%Y-%m-%dT00:00:00.000Z'), 'dateTo': nm_end.strftime('%Y-%m-%dT23:59:59.000Z'), 'from': str(ts_s), 'to': str(ts_e), 'includeFinished': '1', 'view': 'month'}
        if self.org_unit_data_guid:
            data['orgUnitDataGuid'] = self.org_unit_data_guid
        
        try:
            if self.session is None:
                raise RuntimeError("Session initialization failed")
            async with self.session.post(f"{self.base_url}/StaffPortal/duties/data/load.json", headers=self._get_api_headers(), data=data) as resp:
                if resp.status != 200: 
                    logger.error(f"Async Load Error: Status {resp.status}")
                    raise ApiError(f"Status {resp.status}")

                json_data = await resp.json(content_type=None)
                
            duties = parse_personal_duties(json_data, filter_mode, my_name=override_name or self.discovered_name)
            
            # Archive fetch 
            archive = await self.load_archive_duties(now.year, filter_mode)
            
            # Merge logic
            d_map = {d.begin: d for d in duties}
            for ad in archive:
                if ad.begin not in d_map: d_map[ad.begin] = ad
                elif not d_map[ad.begin].location and ad.location: d_map[ad.begin] = ad
            
            duties = sorted(d_map.values(), key=lambda x: x.begin)
            
            # Cache
            ser = [{'begin': d.begin.strftime('%Y-%m-%dT%H:%M:%S'), 'end': d.end.strftime('%Y-%m-%dT%H:%M:%S'), 'vehicle': d.vehicle, 'location': d.location, 'duty_type': d.duty_type, 'crew': d.crew, 'comment': d.comment} for d in duties]
            self._set_cached_data(cache_key, ser)
            return duties
        except Exception as e:
            logger.warning(f"Async Future Duties Error: {e}")
            return []

    async def get_next_duty(self) -> Optional[Duty]:
        duties = await self.load_future_duties(use_cache=True)
        now = datetime.now()
        for d in duties:
            if d.begin > now: return d
        return None

    # Implement other methods similarly (search_staff_contact, load_absences etc.)
    # For now, this core set allows testing basic functionality.
    
    async def load_absences(self) -> List[Dict[str, Any]]:
        await self.ensure_session()
        daily_map: Dict[date, Dict[str, Any]] = {}
        now = datetime.now()
        df = (now - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00.000Z')
        dt = (now + timedelta(days=400)).strftime('%Y-%m-%dT23:59:59.000Z')
        
        holiday_cache: Dict[int, Any] = {}
        def is_h(d: date) -> bool:
            if d.year not in holiday_cache: holiday_cache[d.year] = get_holidays(d.year)
            return d in holiday_cache[d.year]
            
        body = {'max': '1000', 'dateFrom': df, 'dateTo': dt, 'reason': '', 'form.event.onsubmit': 'searchForm'}
        
        async def fetch_abs() -> Optional[Dict[str, Any]]:
            try:
                if not self.session: return None
                async with self.session.post(f"{self.base_url}/StaffPortal/absence/data/load.json", headers=self._get_api_headers(), data=body) as r:
                   return await r.json(content_type=None) if r.status == 200 else None
            except aiohttp.ClientError as e:
                logger.debug(f"Network error fetching absences: {e}")
                return None
            except Exception as e:
                logger.debug(f"Error fetching absences: {e}")
                return None
            
        async def fetch_wishes() -> Optional[Dict[str, Any]]:
            try:
                if not self.session: return None
                async with self.session.post(f"{self.base_url}/StaffPortal/absence/data/loadWishes.json", headers=self._get_api_headers(), data=body) as r:
                   return await r.json(content_type=None) if r.status == 200 else None
            except aiohttp.ClientError as e:
                logger.debug(f"Network error fetching wishes: {e}")
                return None
            except Exception as e:
                logger.debug(f"Error fetching wishes: {e}")
                return None

        res_abs, res_wishes = await asyncio.gather(fetch_abs(), fetch_wishes())
        
        # Logic same as Sync
        if res_abs:
            for item in res_abs.get('data', []):
                reason = item.get('reasonName') or item.get('absenceTypeName') or "Abwesend"
                b, e = fix_datetime(item.get('begin')), fix_datetime(item.get('end'))
                if b and b.hour >= 20: b = (b + timedelta(days=1)).replace(hour=0, minute=0, second=0)
                if not b or not e: continue
                if e.hour == 0 and e.minute == 0: e -= timedelta(seconds=1)
                curr = b.date()
                while curr <= e.date():
                    lbl = reason
                    if is_h(curr): lbl = "Abwesend" if curr.weekday() == 6 else "Geplante Sonderabwesenheit"
                    if curr not in daily_map or is_h(curr) or any(w in lbl.lower() for w in ["urlaub", "abwesend", "krank"]):
                        daily_map[curr] = {'label': lbl, 'fixed': True}
                    curr += timedelta(days=1)

        if res_wishes:
            for item in res_wishes.get('data', []):
                try:
                    state = int(item.get('approvalState'))
                except (ValueError, TypeError):
                    state = 0
                if state not in [0, 1] or item.get('withdrawn') in [1, True]: continue
                reason_str = str(item.get('reasonName') or item.get('absenceTypeName') or "Abwesend")
                status_text = " [yellow](Beantragt)[/yellow]" if state == 0 else " [green](Gen. / n. eingetr.)[/green]"
                b, end_dt = fix_datetime(item.get('begin')), fix_datetime(item.get('end'))
                if b and b.hour >= 20: b = (b + timedelta(days=1)).replace(hour=0, minute=0, second=0)
                if not b or not end_dt: continue
                if end_dt.hour == 0 and end_dt.minute == 0: end_dt -= timedelta(seconds=1)
                curr = b.date()
                while curr <= end_dt.date():
                    if curr not in daily_map or not daily_map[curr].get('fixed'):
                        lbl = reason_str
                        if is_h(curr): lbl = "Abwesend" if curr.weekday() == 6 else "Geplante Sonderabwesenheit"
                        if curr not in daily_map or is_h(curr) or "urlaub" in lbl.lower():
                            daily_map[curr] = {'label': lbl + status_text, 'fixed': False}
                    curr += timedelta(days=1)
        
        # Weekend Logic Reused
        sorted_d = sorted(daily_map.keys())
        for d in sorted_d:
            if d.weekday() == 0: # Monday
                lbl_mon = str(daily_map[d]['label']).lower()
                if "urlaub" in lbl_mon or "sonderabwesenheit" in lbl_mon:
                    prev_sun = d - timedelta(days=1)
                    prev_fri = d - timedelta(days=3)
                    is_connecting = False
                    if prev_fri in daily_map and ("urlaub" in str(daily_map[prev_fri]['label']).lower() or "sonderabwesenheit" in str(daily_map[prev_fri]['label']).lower()):
                        is_connecting = True
                    if is_connecting:
                        if prev_sun not in daily_map or daily_map[prev_sun]['label'] == "Freies Wochenende": daily_map[prev_sun] = {'label': "Abwesend", 'fixed': False}
                    else:
                        if prev_sun not in daily_map or daily_map[prev_sun]['label'] == "Abwesend": daily_map[prev_sun] = {'label': "Freies Wochenende", 'fixed': False}
        
        # Post-Vacation Sunday
        sorted_d = sorted(daily_map.keys())
        for d in sorted_d:
            if d.weekday() == 5 and "urlaub" in str(daily_map[d]['label']).lower():
                sun = d + timedelta(days=1)
                if sun not in daily_map:
                    suffix = " [yellow](Beantragt)[/yellow]" if "[yellow]" in str(daily_map[d]['label']) else (" [green](Gen. / n. eingetr.)[/green]" if "[green]" in str(daily_map[d]['label']) else "")
                    daily_map[sun] = {'label': "Abwesend" + suffix, 'fixed': False}

        results = []
        if not daily_map: return []
        fd = sorted(daily_map.keys())
        curr_s, curr_e, curr_l = fd[0], fd[0], daily_map[fd[0]]['label']
        for i in range(1, len(fd)):
            d = fd[i]
            if d == curr_e + timedelta(days=1) and daily_map[d]['label'] == curr_l: curr_e = d
            else:
                results.append({'begin': datetime.combine(curr_s, datetime.min.time()).strftime('%Y-%m-%dT%H:%M:%S'), 'end': datetime.combine(curr_e, datetime.max.time().replace(microsecond=0)).strftime('%Y-%m-%dT%H:%M:%S'), 'location': '', 'vehicle': '', 'duty_type': curr_l, 'crew': []})
                curr_s, curr_e, curr_l = d, d, daily_map[d]['label']
        results.append({'begin': datetime.combine(curr_s, datetime.min.time()).strftime('%Y-%m-%dT%H:%M:%S'), 'end': datetime.combine(curr_e, datetime.max.time().replace(microsecond=0)).strftime('%Y-%m-%dT%H:%M:%S'), 'location': '', 'vehicle': '', 'duty_type': curr_l, 'crew': []})
        return results


    async def search_staff_contact(self, query: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Search staff contacts with optional caching.
        
        Caches raw staff data per GUID with TTL. Multiple searches use the same 
        cached data, with filtering done locally for performance.
        
        Args:
            query: Search string to filter staff by name.
            use_cache: Whether to use cached data if available.
            
        Returns:
            List of staff contact dictionaries matching the query.
        """
        await self.ensure_session()
        logger.debug(f"Searching staff async: {query}")
        now = datetime.now()
        df, dt = (now - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00.000Z'), (now + timedelta(days=365)).strftime('%Y-%m-%dT23:59:59.000Z')
        
        guids = set()
        if self.org_unit_data_guid: guids.add(self.org_unit_data_guid)
        if self.extra_guids: guids.update(self.extra_guids)
        sorted_guids = sorted([g for g in guids if g])
        
        async def fetch_one(g: str) -> Optional[Dict[str, Any]]:
            """Fetch raw staff data for a single GUID, using cache if available."""
            cache_key = f"staff_raw_{g}"
            
            # Check cache first
            if use_cache:
                cached = self._get_cached_data(cache_key)
                if cached is not None and isinstance(cached, dict):
                    logger.debug(f"Staff cache hit for GUID {g[:8]}...")
                    return cast(Dict[str, Any], cached)
            
            # Fetch from API
            try:
                if not self.session: return None
                data = {'orgUnitDataGuid': g, 'withSubOrgUnits': 'true', 'loadModelData': '1', 'dateFrom': df, 'dateTo': dt}
                async with self.session.post(f"{self.base_url}/StaffPortal/staff/data/getStaff.json", headers=self._get_api_headers(), data=data) as resp:
                    if resp.status == 200:
                        j = await resp.json(content_type=None)
                        # Cache raw data
                        self._set_cached_data(cache_key, j)
                        return cast(Dict[str, Any], j)
            except aiohttp.ClientError as e:
                logger.debug(f"Network error fetching staff: {e}")
            except Exception as e:
                logger.debug(f"Error fetching staff: {e}")
            return None

        # Fetch all GUIDs in parallel (cached ones return instantly)
        raw_results = await asyncio.gather(*[fetch_one(g) for g in sorted_guids])
        
        # Parse and filter locally
        parsed_results: List[List[Dict[str, Any]]] = []
        for raw in raw_results:
            if raw:
                parsed_results.append(parse_staff_contact(raw, query))
        
        # Merge and deduplicate
        flat: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for r_list in parsed_results:
            for item in r_list:
                pnr = item.get('personalnummer')
                name = item.get('_display_name')
                key = str(pnr) if pnr else str(name)
                if key not in seen:
                    flat.append(item)
                    seen.add(key)
        
        flat.sort(key=lambda x: x.get('_display_name', ''))
        return flat
    async def load_my_event_duties(self) -> List[Duty]:
        await self.ensure_session()
        df = datetime.now().strftime('%Y-%m-%dT00:00:00.000Z')
        dt = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%dT23:59:59.000Z')
        try:
            guid = self.org_unit_data_guid
            if not guid: return []
            if not self.session: await self.ensure_session()
            if self.session is None:
                raise RuntimeError("Session initialization failed")
            async with self.session.post(f"{self.base_url}/StaffPortal/duties/data/loadInRange.json", headers=self._get_api_headers(), data={'orgUnitDataGuid': guid, 'withSubOrgUnits': '0', 'dateFrom': df, 'dateTo': dt, 'forEvents': 'true', 'loadDutiesForAllRessources': '0'}) as resp:
                if resp.status == 200:
                    return parse_personal_duties(await resp.json(content_type=None), filter_mode='include_all')
        except Exception as e:
            logger.warning(f"Failed to load personal event duties: {e}")
        return []

    async def load_daily_plan(self, date: datetime, use_cache: bool = True) -> List[Dict[str, Any]]:
        cache_key = f"daily_{date.strftime('%Y-%m-%d')}"
        if use_cache:
            cached = self._get_cached_data(cache_key)
            if cached: 
                 # Hydrate simple dicts
                 hydrated = []
                 for item in cached:
                     ni = item.copy()
                     if isinstance(ni.get('begin'), str): ni['begin'] = datetime.strptime(ni['begin'], '%Y-%m-%dT%H:%M:%S')
                     if isinstance(ni.get('end'), str): ni['end'] = datetime.strptime(ni['end'], '%Y-%m-%dT%H:%M:%S')
                     hydrated.append(ni)
                 return hydrated

        sd, ed = date.replace(hour=0, minute=0, second=0, microsecond=0), date.replace(hour=23, minute=59, second=59, microsecond=999999)
        try:
            results = await self._fetch_daily_plan_items(sd, ed)
            serializable = [{'begin': i['begin'].strftime('%Y-%m-%dT%H:%M:%S') if isinstance(i.get('begin'), datetime) else i.get('begin'), 'end': i['end'].strftime('%Y-%m-%dT%H:%M:%S') if isinstance(i.get('end'), datetime) else i.get('end'), 'vehicle': i['vehicle'], 'crew': i['crew']} for i in results]
            self._set_cached_data(cache_key, serializable)
            return results
        except aiohttp.ClientError as e:
            logger.debug(f"Network error loading daily plan: {e}")
            return []
        except Exception as e:
            logger.debug(f"Error loading daily plan: {e}")
            return []

    async def _fetch_daily_plan_items(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        if not self.session: await self.ensure_session()
        if self.session is None:
            raise RuntimeError("Session initialization failed")
        df, dt = (date_from - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z'), (date_to + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
        
        guids_set = {self.org_unit_data_guid} if self.org_unit_data_guid else set()
        guids_set.update(self.extra_guids)
        # Removed unused DEFAULT_GUID
        guids_list = list(guids_set)
        
        # Phase 1: Discover extra GUIDs from duties
        try:
            async with self.session.post(f"{self.base_url}/StaffPortal/duties/data/load.json", headers=self._get_api_headers(), data={'max': '20'}) as d_resp:
                if d_resp.status == 200:
                    j = await d_resp.json(content_type=None)
                    for item in j.get('data', []):
                        og = item.get('orgUnitDataGuid')
                        if og and og not in guids_list: guids_list.append(og)
        except Exception as e:
            logger.warning(f"Failed to fetch initial daily plan data: {e}")

        # Phase 2: Parallel Fetch
        async def fetch_plan(g: str) -> Optional[Dict[str, Any]]:
            try:
                # self.session is asserted above
                if not self.session: return None
                async with self.session.post(f"{self.base_url}/StaffPortal/plan/data/loadPlan.json", headers=self._get_api_headers(), data={'orgUnitDataGuid': g, 'withSubOrgUnits': '1', 'dateFrom': df, 'dateTo': dt, 'sortPlan': 'false'}) as r:
                    if r.status == 200:
                        return cast(Dict[str, Any], await r.json(content_type=None))
            except aiohttp.ClientError as e:
                logger.debug(f"Network error fetching plan: {e}")
            except Exception as e:
                logger.debug(f"Error fetching plan: {e}")
            return None

        plan_results = await asyncio.gather(*[fetch_plan(g) for g in guids_list if g])
        
        results, seen = [], set()
        for data in plan_results:
            if data and data.get('data'):
                for item in parse_daily_plan_raw(data):
                    if item['begin'] and item['end'] and not (item['end'] < date_from or item['begin'] > date_to):
                        sig = (item['vehicle'], item['begin'], item['end'], tuple(sorted(item['crew'].items())))
                        if sig not in seen: seen.add(sig); results.append(item)
        return results

