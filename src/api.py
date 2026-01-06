import requests
from urllib3.util.retry import Retry
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional, List, Dict, Any, Tuple, Union

from src.config import console, DEFAULT_GUID
from src.utils import TimeoutHTTPAdapter

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

    def _get_api_headers(self) -> Dict[str, str]:
        headers = {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest', 'User-Agent': self.user_agent}
        if self.header_key and self.header_value:
            headers[self.header_key] = self.header_value
        return headers

    def _fix_datetime(self, s: Optional[str]) -> Optional[datetime]:
        """Helper to fix datetime strings from API."""
        if not s: return None
        try:
            # Parse as UTC (assuming 'Z' at end implies UTC or it's raw UTC time)
            dt = datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
            import time
            # Simple offset calculation
            offset = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
            local_dt = dt + timedelta(seconds=offset)
            return local_dt
        except Exception: return None

    def _fetch_daily_plan_items(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/StaffPortal/plan/data/loadPlan.json"
        
        # Buffer dates slightly to ensure coverage
        df = (date_from - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
        dt = (date_to + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
        
        guids: List[Optional[str]] = [self.org_unit_data_guid]
        if self.extra_guids:
            guids.extend(self.extra_guids)
        else:
             guids.append(DEFAULT_GUID)

        # Try to find more GUIDs via personal duties load (hacky but useful discovery)
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
                        # Parse without strict single-day filtering
                        plan = self._parse_daily_plan_raw(data)
                        for item in plan:
                            # Filter by requested date range here
                            if item['begin'] and item['end']:
                                # naive check
                                if item['end'] < date_from or item['begin'] > date_to:
                                    continue
                                
                                # Deduplication
                                crew_sig = tuple(sorted(item['crew'].items()))
                                sig = (item['vehicle'], item['begin'], item['end'], crew_sig)
                                if sig not in seen_signatures:
                                    seen_signatures.add(sig)
                                    results.append(item)
            except Exception as e:
                console.print(f"[warning]Fehler beim Laden von GUID {g}: {e}[/warning]")
                continue
        return results

    def load_archive_duties(self, year: int) -> List[Dict[str, Any]]:
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
                return self._parse_personal_duties(resp.json())
        except Exception as e:
            console.print(f"[warning]Fehler beim Laden des Archivs ({year}): {e}[/warning]")
        return []

    def load_future_duties(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/StaffPortal/duties/data/load.json"
        duties: List[Dict[str, Any]] = []
        
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Go back one day to be safe with timezones for the 1st of the month
        start_fetch = start_of_month - timedelta(days=1)
        
        # Calculate end of next month
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

        # 1. Load Standard Future Duties
        try:
            resp = self.session.post(url, headers=self._get_api_headers(), data=body)
            resp.raise_for_status()
            duties = self._parse_personal_duties(resp.json())
        except Exception as e:
            console.print(f"[warning]Fehler beim Laden der Dienste: {e}[/warning]")
        
        # 2. Load Archive for Current Year to ensure past duties (of current year) have locations
        # and to catch any duties missing from load.json
        archive_duties = self.load_archive_duties(now.year)
        
        # Merge logic: Use dictionary keyed by begin time to deduplicate
        # Prefer archive_duties for past events if they have location? 
        # Actually archive duties generally have location.
        
        duty_map = {d['begin']: d for d in duties}
        
        for ad in archive_duties:
            begin = ad['begin']
            # If not present, add it.
            # If present, check if existing one lacks location (which was the bug).
            # But load.json usually has location. The bug was when using daily_plan fallback.
            # So here, archive should be good. 
            # We can overwrite if we trust archive more for past.
            # But load.json is better for FUTURE.
            
            # Simple heuristic: If it's in the past (relative to now), prefer Archive (or just add if missing).
            # If it's in the future, prefer Load.json.
            
            if begin not in duty_map:
                duty_map[begin] = ad
            else:
                # Exists. Check location.
                if not duty_map[begin].get('location') and ad.get('location'):
                    duty_map[begin] = ad

        duties = list(duty_map.values())
        duties.sort(key=lambda x: x['begin'])
        return duties

    def load_daily_plan(self, date: datetime) -> List[Dict[str, Any]]:
        # Reuse the new fetch method but filter strictly for the day
        start_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return self._fetch_daily_plan_items(start_day, end_day)

    def _parse_personal_duties(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        # Removed "wochenende" from filter to avoid filtering actual weekend shifts
        filter_words = ["urlaub", "frei", "wunsch", "abwesenheit", "pflege", "krank", "zeitausgleich", "sonderabwesenheit", "ersatzruhe", "ruhetag"]
        for item in data.get('data', []):
            duty_type, location = str(item.get('dutyTypeName', '')), str(item.get('orgUnitName', ''))
            alloc = item.get('allocationInfo', {})
            if isinstance(alloc, dict): al = next(iter(alloc.values())) if alloc.values() else []
            else: al = alloc if isinstance(alloc, list) else []
            content_str = (duty_type + location + str(al)).lower()
            if any(word in content_str for word in filter_words): continue
            
            dt_obj = self._fix_datetime(item.get('begin', ''))
            end_obj = self._fix_datetime(item.get('end', ''))
            if not dt_obj or not end_obj: continue

            vehicle = ""
            crew = []
            if len(al) > 1:
                last_val = str(al[-1])
                # Check if last_val is likely a vehicle (starts with digit or contains known vehicle types)
                is_vehicle = last_val and (last_val[0].isdigit() or any(vtype in last_val.upper() for vtype in ["RTW", "KTW", "BTW", "NEF", "BKTW", "VEF"]))
                
                if is_vehicle:
                    vehicle = last_val
                    crew = [str(x) for x in al[1:-1]]
                else:
                    vehicle = ""
                    crew = [str(x) for x in al[1:]]
            elif len(al) == 1:
                # Only position or only name? Usually al[0] is position. 
                # But if only one element is there, we treat it as unknown/crew if it's not a vehicle
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
        """Parses daily plan data without filtering by date."""
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
