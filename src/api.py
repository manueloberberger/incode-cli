import requests
import time
import json
import os
import re
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional, List, Dict, Any, Tuple, Union

from src.config import console, DEFAULT_GUID
from src.utils import TimeoutHTTPAdapter

CACHE_FILE = ".incode_cache.json"
CACHE_TTL = 900  # 15 Minutes validity

class IncodeRequests:
    def __init__(self, base_url: str, extra_guids: Optional[List[str]] = None) -> None:
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = TimeoutHTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.header_key: Optional[str] = None
        self.header_value: Optional[str] = None
        self.org_unit_data_guid: Optional[str] = None
        self.base_url: str = base_url
        self.extra_guids: List[str] = extra_guids if extra_guids else []
        self.user_agent: str = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Loads the cache file if it exists."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Saves current memory cache to file."""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[warning]Cache konnte nicht gespeichert werden: {e}[/warning]")

    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Returns cached data if valid (TTL), otherwise None."""
        if key in self.cache:
            entry = self.cache[key]
            timestamp = entry.get('timestamp', 0)
            if time.time() - timestamp < CACHE_TTL:
                return entry.get('data')
        return None

    def _set_cached_data(self, key: str, data: Any):
        """Updates cache for a specific key."""
        self.cache[key] = {
            'timestamp': time.time(),
            'data': data
        }
        self._save_cache()

    def login(self, username, password) -> Tuple[bool, str]:
        login_url = f"{self.base_url}/login.php"
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Authentifizierung...", total=None)
            login_headers = {'User-Agent': self.user_agent, 'Content-Type': 'application/x-www-form-urlencoded'}
            login_body = {'client': 'dienstplan', 'login': username, 'password': password}
            try:
                self.session.post(login_url, headers=login_headers, data=login_body)
                if 'PHPSESSID' not in self.session.cookies: return False, "Login fehlgeschlagen."
                
                # Fetch headers and tokens
                resp = self.session.get(f"{self.base_url}/", headers={'User-Agent': self.user_agent})
                content = resp.text
                inc_m = re.search(r'''['"](x-incode-[^'" ]+)['"]\s*:\s*['"]([^'" ]+)['"]''', content)
                if inc_m: self.header_key, self.header_value = inc_m.group(1), inc_m.group(2)
                
                dispo_resp = self.session.get(f"{self.base_url}/StaffPortal/dispo.php", headers={'User-Agent': self.user_agent})
                guids = re.findall(r'''["']orgUnitDataGuid["']\s*:\s*["']([^"]+)["']''', dispo_resp.text)
                if guids: self.org_unit_data_guid = guids[-1]
                else:
                    guids = re.findall(r'''["']orgUnitDataGuid["']\s*:\s*["']([^"]+)["']''', content)
                    if guids: self.org_unit_data_guid = guids[-1]
                
                if not self.header_key:
                    soup = BeautifulSoup(content, 'html.parser')
                    for s in soup.find_all('script'):
                        if s.get('src'):
                            js_url = s.get('src') if s.get('src').startswith('http') else f"{self.base_url}/{s.get('src').lstrip('/')}"
                            try:
                                js_resp = self.session.get(js_url, headers={'User-Agent': self.user_agent})
                                js = js_resp.text
                                m = re.search(r'''['"](x-incode-[^'" ]+)['"]\s*:\s*['"]([^'" ]+)['"]''', js)
                                if m: self.header_key, self.header_value = m.group(1), m.group(2)
                                g = re.findall(r'''["']orgUnitDataGuid["']\s*:\s*["']([^"]+)["']''', js)
                                if g: self.org_unit_data_guid = g[-1]
                            except Exception as e:
                                console.print(f"[warning]JS Parsing warning: {e}[/warning]")
                        if self.header_key: break
                return True, "Eingeloggt."
            except Exception as e: return False, f"Fehler: {e}"

    def search_staff_contact(self, query_name: str) -> List[Dict[str, str]]:
        """
        Searches for a colleague's contact info (Phone, Email, etc.) using getStaff.json.
        """
        url = f"{self.base_url}/StaffPortal/staff/data/getStaff.json"
        
        # We need a valid range to get active staff. Let's take current year +/- 1 year
        now = datetime.now()
        df = (now - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00.000Z')
        dt = (now + timedelta(days=365)).strftime('%Y-%m-%dT23:59:59.000Z')
        
        body = {
            'orgUnitDataGuid': self.org_unit_data_guid or DEFAULT_GUID,
            'withSubOrgUnits': 'true',
            'loadModelData': '1',
            'dateFrom': df,
            'dateTo': dt
        }

        try:
            resp = self.session.post(url, headers=self._get_api_headers(), data=body)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_staff_contact(data, query_name)
        except Exception as e:
            console.print(f"[warning]Fehler bei der Mitarbeitersuche: {e}[/warning]")
        return []

    def _parse_staff_contact(self, data: Dict[str, Any], query_name: str) -> List[Dict[str, Any]]:
        """
        Returns the FULL raw data object for matching staff members to allow detailed inspection.
        """
        results = []
        staff_list = data.get('data', [])
        
        q = query_name.lower()
        
        for p in staff_list:
            first = str(p.get('vorname', '')).strip()
            last = str(p.get('nachname', '')).strip()
            full_name = f"{first} {last}".strip()
            if not full_name:
                full_name = str(p.get('name', '')).strip()

            # Search in Name, Personalnummer or Email
            search_text = (full_name + str(p.get('personalnummer', '')) + str(p.get('email', ''))).lower()
            
            # Also search in occupations (for service numbers like 2067 in "2067.7 BERUF" or "206707")
            for occ in p.get('ressourceToOccupations', []):
                search_text += str(occ.get('name', '')).lower()
                search_text += str(occ.get('externalId', '')).lower()
                search_text += str(occ.get('ressourceIndicator', '')).lower()
            
            if q in search_text:
                # Return the full raw object, but add a convenient display name
                p['_display_name'] = full_name
                results.append(p)
        
        # Sort by name
        results.sort(key=lambda x: x.get('_display_name', ''))
        return results

    def _extract_role(self, person_data: Dict[str, Any]) -> str:
        """Helper to find the main role (Beruf, Zivi, Freiwillig)"""
        roles = []
        occupations = person_data.get('ressourceToOccupations', [])
        for occ in occupations:
            name = occ.get('name', '')
            if name: roles.append(name)
        return ", ".join(roles) if roles else "-"

    def _get_api_headers(self) -> Dict[str, str]:
        headers = {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest', 'User-Agent': self.user_agent}
        if self.header_key and self.header_value:
            headers[self.header_key] = self.header_value
        return headers

    def _fix_datetime(self, s: Optional[str]) -> Optional[datetime]:
        """Helper to fix datetime strings from API."""
        if not s: return None
        try:
            dt = datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
            offset = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
            local_dt = dt + timedelta(seconds=offset)
            return local_dt
        except Exception: return None

    def _fetch_daily_plan_items(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/StaffPortal/plan/data/loadPlan.json"
        
        df = (date_from - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
        dt = (date_to + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
        
        guids: List[Optional[str]] = [self.org_unit_data_guid]
        if self.extra_guids:
            guids.extend(self.extra_guids)
        else:
             guids.append(DEFAULT_GUID)

        try:
            d_resp = self.session.post(f"{self.base_url}/StaffPortal/duties/data/load.json", headers=self._get_api_headers(), data={'max': '20'})
            if d_resp.status_code == 200:
                for item in d_resp.json().get('data', []):
                    og = item.get('orgUnitDataGuid')
                    if og and og not in guids: guids.append(og)
        except Exception: pass
        
        unique_guids = list(set([g for g in guids if g]))
        results = []
        seen_signatures = set()

        for g in unique_guids:
            body = {'orgUnitDataGuid': g, 'withSubOrgUnits': '1', 'dateFrom': df, 'dateTo': dt, 'sortPlan': 'false'}
            try:
                r = self.session.post(url, headers=self._get_api_headers(), data=body)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('data'): 
                        plan = self._parse_daily_plan_raw(data)
                        for item in plan:
                            if item['begin'] and item['end']:
                                if item['end'] < date_from or item['begin'] > date_to:
                                    continue
                                crew_sig = tuple(sorted(item['crew'].items()))
                                sig = (item['vehicle'], item['begin'], item['end'], crew_sig)
                                if sig not in seen_signatures:
                                    seen_signatures.add(sig)
                                    results.append(item)
            except Exception as e:
                console.print(f"[warning]Fehler beim Laden von GUID {g}: {e}[/warning]")
                continue
        return results

    def _get_holidays(self, year: int) -> List[datetime.date]:
        """Returns a list of Austrian holidays for the given year."""
        holidays = [
            datetime(year, 1, 1).date(), datetime(year, 1, 6).date(),
            datetime(year, 5, 1).date(), datetime(year, 8, 15).date(),
            datetime(year, 10, 26).date(), datetime(year, 11, 1).date(),
            datetime(year, 12, 8).date(), datetime(year, 12, 24).date(),
            datetime(year, 12, 25).date(), datetime(year, 12, 26).date(),
            datetime(year, 12, 31).date()
        ]
        # Easter
        a = year % 19; b = year // 100; c = year % 100
        d = b // 4; e = b % 4; f = (b + 8) // 25
        g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
        i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        easter = datetime(year, month, day).date()
        holidays.extend([easter + timedelta(days=1), easter + timedelta(days=39), easter + timedelta(days=50), easter + timedelta(days=60)])
        return holidays

    def load_absences(self) -> List[Dict[str, Any]]:
        """
        Loads absences using day-by-day logic to correctly handle holidays, weekends, and gaps.
        """
        results = []
        daily_map = {} # date -> {'label': str, 'fixed': bool}

        now = datetime.now()
        # Look back 30 days, forward 400 days
        start_date = now - timedelta(days=30)
        end_date = now + timedelta(days=400)
        
        date_from_str = start_date.strftime('%Y-%m-%dT00:00:00.000Z')
        date_to_str = end_date.strftime('%Y-%m-%dT23:59:59.000Z')

        def normalize_start_date(dt):
            if dt.hour >= 20: return (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0)
            return dt

        holiday_cache = {}
        def is_holiday(d):
            if d.year not in holiday_cache:
                holiday_cache[d.year] = self._get_holidays(d.year)
            return d in holiday_cache[d.year]

        # 1. FIXED ROSTER (load.json)
        url_abs = f"{self.base_url}/StaffPortal/absence/data/load.json"
        body = {'max': '1000', 'dateFrom': date_from_str, 'dateTo': date_to_str, 'reason': '', 'form.event.onsubmit': 'searchForm'}
        
        try:
            resp = self.session.post(url_abs, headers=self._get_api_headers(), data=body)
            if resp.status_code == 200:
                for item in resp.json().get('data', []):
                    reason = item.get('reasonName') or item.get('absenceTypeName') or "Abwesend"
                    dt_start = normalize_start_date(self._fix_datetime(item.get('begin')))
                    dt_end = self._fix_datetime(item.get('end'))
                    if not dt_start or not dt_end: continue
                    if dt_end.hour == 0 and dt_end.minute == 0: dt_end -= timedelta(seconds=1)

                    curr = dt_start.date()
                    while curr <= dt_end.date():
                        label = reason
                        # Split by Holiday if it's Urlaub
                        if "urlaub" in reason.lower() and is_holiday(curr):
                            label = "Geplante Sonderabwesenheit"
                        
                        daily_map[curr] = {'label': label, 'fixed': True}
                        curr += timedelta(days=1)
        except Exception as e:
            console.print(f"[warning]Fehler (Fixed): {e}[/warning]")

        # 2. WISHES (loadWishes.json)
        url_wish = f"{self.base_url}/StaffPortal/absence/data/loadWishes.json"
        try:
            resp = self.session.post(url_wish, headers=self._get_api_headers(), data=body)
            if resp.status_code == 200:
                for item in resp.json().get('data', []):
                    try:
                        state = int(item.get('approvalState'))
                    except: state = 0
                    
                    if state != 1: continue
                    if item.get('withdrawn') == 1 or item.get('withdrawn') is True: continue

                    reason = item.get('reasonName') or item.get('absenceTypeName') or "Abwesend"
                    dt_start = normalize_start_date(self._fix_datetime(item.get('begin')))
                    dt_end = self._fix_datetime(item.get('end'))
                    if not dt_start or not dt_end: continue
                    if dt_end.hour == 0 and dt_end.minute == 0: dt_end -= timedelta(seconds=1)

                    curr = dt_start.date()
                    while curr <= dt_end.date():
                        # Don't overwrite fixed items
                        if curr in daily_map and daily_map[curr]['fixed']:
                            curr += timedelta(days=1)
                            continue
                        
                        label = reason
                        if "urlaub" in reason.lower() and is_holiday(curr):
                            label = "Geplante Sonderabwesenheit"
                        
                        label += " [green](Gen. / n. eingetr.)[/green]"
                        
                        daily_map[curr] = {'label': label, 'fixed': False}
                        curr += timedelta(days=1)
        except Exception as e:
            console.print(f"[warning]Fehler (Wishes): {e}[/warning]")

        # 3. SUNDAY FILLER
        sorted_dates = sorted(daily_map.keys())
        sunday_adds = []
        
        for d in sorted_dates:
            if d.weekday() == 5: # Saturday
                info = daily_map[d]
                if "urlaub" in info['label'].lower():
                    sunday = d + timedelta(days=1)
                    if sunday not in daily_map:
                        lbl = "Abwesend"
                        if "[green]" in info['label']:
                            lbl += " [green](Gen. / n. eingetr.)[/green]"
                        sunday_adds.append((sunday, lbl))
        
        for d, lbl in sunday_adds:
            daily_map[d] = {'label': lbl, 'fixed': False}

        # 4. CONDENSE
        if not daily_map: return []
        
        final_dates = sorted(daily_map.keys())
        
        current_block_start = final_dates[0]
        current_block_end = final_dates[0]
        current_label = daily_map[final_dates[0]]['label']
        
        for i in range(1, len(final_dates)):
            d = final_dates[i]
            label = daily_map[d]['label']
            
            if d == current_block_end + timedelta(days=1) and label == current_label:
                current_block_end = d
            else:
                start_ts = datetime.combine(current_block_start, datetime.min.time())
                end_ts = datetime.combine(current_block_end, datetime.max.time().replace(microsecond=0))
                results.append({
                    'begin': start_ts.strftime('%Y-%m-%dT%H:%M:%S'),
                    'end': end_ts.strftime('%Y-%m-%dT%H:%M:%S'),
                    'location': '', 'vehicle': '', 
                    'duty_type': current_label, 'crew': []
                })
                
                current_block_start = d
                current_block_end = d
                current_label = label
        
        start_ts = datetime.combine(current_block_start, datetime.min.time())
        end_ts = datetime.combine(current_block_end, datetime.max.time().replace(microsecond=0))
        results.append({
            'begin': start_ts.strftime('%Y-%m-%dT%H:%M:%S'),
            'end': end_ts.strftime('%Y-%m-%dT%H:%M:%S'),
            'location': '', 'vehicle': '', 
            'duty_type': current_label, 'crew': []
        })

        return results

    def _parse_absences_raw(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        # Support both 'data' list or direct list if API differs
        items = data.get('data', [])
        if not isinstance(items, list): return []
        
        for item in items:
            # Inspection of fields (speculative but common):
            # 'absenceTypeName' or 'type', 'begin', 'end', 'reason'
            
            # Try to map to our common structure
            duty_type = item.get('absenceTypeName') or item.get('type') or item.get('text') or "Abwesenheit"
            comment = item.get('comment') or ""
            
            dt_obj = self._fix_datetime(item.get('begin', ''))
            end_obj = self._fix_datetime(item.get('end', ''))
            
            if not dt_obj or not end_obj: continue
            
            results.append({
                'begin': dt_obj.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': end_obj.strftime('%Y-%m-%dT%H:%M:%S'),
                'location': '',
                'vehicle': '',
                'duty_type': f"{duty_type} {comment}".strip(),
                'crew': []
            })
            
        return results

    def load_archive_duties(self, year: int, filter_mode: str = 'exclude_absences') -> List[Dict[str, Any]]:
        url = f"{self.base_url}/StaffPortal/archive/data/loadDuties.json"
        body = {
            'year': str(year),
            'month': '',
            'dateDescendingSort': 'true',
            'orgUnit': '',
            'withSubOrgs': 'on',
            'form.event.onsubmit': 'searchForm',
        }
        try:
            resp = self.session.post(url, headers=self._get_api_headers(), data=body)
            if resp.status_code == 200:
                return self._parse_personal_duties(resp.json(), filter_mode)
        except Exception as e:
            console.print(f"[warning]Fehler beim Laden des Archivs ({year}): {e}[/warning]")
        return []

    def load_future_duties(self, use_cache=True, filter_mode: str = 'exclude_absences') -> List[Dict[str, Any]]:
        """
        Loads future duties/absences.
        filter_mode options: 'exclude_absences' (default), 'only_absences', 'include_all'
        """
        cache_key = f"future_duties_{filter_mode}"
        
        if use_cache:
            cached = self._get_cached_data(cache_key)
            if cached:
                return cached

        url = f"{self.base_url}/StaffPortal/duties/data/load.json"
        duties: List[Dict[str, Any]] = []
        
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_fetch = start_of_month - timedelta(days=1)
        
        if now.month == 12: next_month = now.replace(year=now.year + 1, month=1, day=1)
        else: next_month = now.replace(month=now.month + 1, day=1)
        
        if next_month.month == 12: next_month_end = next_month.replace(year=next_month.year + 1, month=1, day=1) - timedelta(seconds=1)
        else: next_month_end = next_month.replace(month=next_month.month + 1, day=1) - timedelta(seconds=1)
        
        ts_start = int(start_fetch.timestamp())
        ts_end = int(next_month_end.timestamp())
        
        body = {
            'max': '1000',
            'dateFrom': start_fetch.strftime('%Y-%m-%dT00:00:00.000Z'),
            'dateTo': next_month_end.strftime('%Y-%m-%dT23:59:59.000Z'),
            'from': str(ts_start),
            'to': str(ts_end),
            'start': str(ts_start),
            'end': str(ts_end),
            'includeFinished': '1',
            'view': 'month' 
        }

        try:
            resp = self.session.post(url, headers=self._get_api_headers(), data=body)
            resp.raise_for_status()
            duties = self._parse_personal_duties(resp.json(), filter_mode)
            
            # Additional fetch from archive (only for duties, archive usually doesn't show future absences reliably or duplicates)
            # For simplicity, if we want absences, we rely on the main load.json which should have them.
            # Archive loading is mostly for past duties which might be missing from load.json rolling window?
            # Existing logic:
            archive_duties = self.load_archive_duties(now.year, filter_mode)
            duty_map = {d['begin']: d for d in duties}
            for ad in archive_duties:
                begin = ad['begin']
                if begin not in duty_map:
                    duty_map[begin] = ad
                else:
                    if not duty_map[begin].get('location') and ad.get('location'):
                        duty_map[begin] = ad

            duties = list(duty_map.values())
            duties.sort(key=lambda x: x['begin'])
            
            # Save to cache
            self._set_cached_data(cache_key, duties)
            return duties
            
        except Exception as e:
            console.print(f"[warning]Fehler beim Laden (Netzwerk): {e}[/warning]")
            # Fallback to cache even if expired
            if cache_key in self.cache:
                console.print("[yellow]Verwende veraltete Cache-Daten (Offline-Modus)[/yellow]")
                return self.cache[cache_key]['data']
            return []

    def load_daily_plan(self, date: datetime, use_cache=True) -> List[Dict[str, Any]]:
        date_str = date.strftime('%Y-%m-%d')
        cache_key = f"daily_{date_str}"
        
        if use_cache:
            cached = self._get_cached_data(cache_key)
            if cached: 
                # Convert strings back to datetime objects for internal logic if needed
                # But wait, results are dicts. The calling code (ui.py) often expects datetime objects 
                # OR handles strings. The original _parse_daily_plan_raw returns datetime objects.
                # JSON serialization turns them to strings.
                # We need to re-hydrate them.
                return self._rehydrate_cache(cached)

        start_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        try:
            results = self._fetch_daily_plan_items(start_day, end_day)
            
            # Serialize for cache (datetimes to iso strings)
            serializable = []
            for item in results:
                new_item = item.copy()
                if isinstance(new_item.get('begin'), datetime):
                    new_item['begin'] = new_item['begin'].strftime('%Y-%m-%dT%H:%M:%S')
                if isinstance(new_item.get('end'), datetime):
                    new_item['end'] = new_item['end'].strftime('%Y-%m-%dT%H:%M:%S')
                serializable.append(new_item)
            
            self._set_cached_data(cache_key, serializable)
            return results
        except Exception as e:
            console.print(f"[warning]Fehler beim Laden des Tagesplans: {e}[/warning]")
            if cache_key in self.cache:
                console.print("[yellow]Lade Cache...[/yellow]")
                return self._rehydrate_cache(self.cache[cache_key]['data'])
            return []

    def _rehydrate_cache(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts date strings back to datetime objects for the application."""
        hydrated = []
        for item in data:
            new_item = item.copy()
            if isinstance(new_item.get('begin'), str):
                new_item['begin'] = datetime.strptime(new_item['begin'], '%Y-%m-%dT%H:%M:%S')
            if isinstance(new_item.get('end'), str):
                new_item['end'] = datetime.strptime(new_item['end'], '%Y-%m-%dT%H:%M:%S')
            hydrated.append(new_item)
        return hydrated

    def _parse_personal_duties(self, data: Dict[str, Any], filter_mode: str = 'exclude_absences') -> List[Dict[str, Any]]:
        results = []
        filter_words = ["urlaub", "frei", "wunsch", "abwesenheit", "abwesend", "pflege", "krank", "zeitausgleich", "sonderabwesenheit", "ersatzruhe", "ruhetag", "seminar", "fortbildung", "schulung"]
        for item in data.get('data', []):
            duty_type = item.get('dutyTypeName') or item.get('absenceTypeName') or item.get('type') or item.get('text') or ""
            duty_type = str(duty_type)

            location = str(item.get('orgUnitName', ''))
            comment = str(item.get('comment', ''))

            alloc = item.get('allocationInfo', {})
            if isinstance(alloc, dict): al = next(iter(alloc.values())) if alloc.values() else []
            else: al = alloc if isinstance(alloc, list) else []
            
            content_str = (duty_type + location + comment + str(al)).lower()
            
            # Check for explicit absence indicators from API fields
            is_explicit_absence = bool(item.get('absenceTypeName'))
            
            # Check for keywords
            is_text_absence = any(word in content_str for word in filter_words)
            
            is_absence = is_explicit_absence or is_text_absence
            
            if filter_mode == 'exclude_absences' and is_absence: continue
            if filter_mode == 'only_absences' and not is_absence: continue
            
            dt_obj = self._fix_datetime(item.get('begin', ''))
            end_obj = self._fix_datetime(item.get('end', ''))
            if not dt_obj or not end_obj: continue

            vehicle = ""
            crew = []
            if len(al) > 1:
                last_val = str(al[-1])
                is_vehicle = last_val and (last_val[0].isdigit() or any(vtype in last_val.upper() for vtype in ["RTW", "KTW", "BTW", "NEF", "BKTW", "VEF"]))
                if is_vehicle:
                    vehicle = last_val
                    crew = [str(x) for x in al[1:-1]]
                else:
                    vehicle = ""
                    crew = [str(x) for x in al[1:]]
            elif len(al) == 1:
                pass

            results.append({
                'begin': dt_obj.strftime('%Y-%m-%dT%H:%M:%S'), 
                'end': end_obj.strftime('%Y-%m-%dT%H:%M:%S'), 
                'location': location, 
                'vehicle': vehicle, 
                'duty_type': duty_type, 
                'crew': crew
            })
        return results

    def _parse_daily_plan_raw(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        items = data.get('data', {})
        it = items.values() if isinstance(items, dict) else items
        
        for i in it:
            pg = i.get('parentDataGuid')
            if not pg: continue
            if pg not in grouped: grouped[pg] = {"crew": {}, "vehicle": "", "begin": None, "end": None}
            eid = str(i.get('externalId', '')).upper()
            rn = str(i.get('additionalInfos', {}).get('ressource_name', '')).strip()
            
            curr_begin = self._fix_datetime(i.get('begin', ''))
            curr_end = self._fix_datetime(i.get('end', ''))
            
            if eid == "KFZ":
                grouped[pg]["vehicle"] = rn
                grouped[pg]["begin"], grouped[pg]["end"] = curr_begin, curr_end
            elif eid in ["FAHRER", "SANITAETER1", "SANITAETER2"] and rn:
                grouped[pg]["crew"][eid] = rn
                if not grouped[pg]["begin"]:
                    grouped[pg]["begin"], grouped[pg]["end"] = curr_begin, curr_end
                    
        return [v for v in grouped.values() if v["begin"] and v["end"]]