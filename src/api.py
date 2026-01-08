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
        self.user_agent: str = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15'
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[warning]Cache konnte nicht gespeichert werden: {e}[/warning]")

    def _get_cached_data(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache[key]
            timestamp = entry.get('timestamp', 0)
            if time.time() - timestamp < CACHE_TTL:
                return entry.get('data')
        return None

    def _set_cached_data(self, key: str, data: Any):
        self.cache[key] = {'timestamp': time.time(), 'data': data}
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
                
                resp = self.session.get(f"{self.base_url}/", headers={'User-Agent': self.user_agent})
                content = resp.text
                inc_m = re.search(r'''['"](x-incode-[^'" ]+)['"]\s*:\s*['"]([^'" ]+)['"]''', content)
                if inc_m: self.header_key, self.header_value = inc_m.group(1), inc_m.group(2)
                
                dispo_resp = self.session.get(f"{self.base_url}/StaffPortal/dispo.php", headers={'User-Agent': self.user_agent})
                guids = re.findall(r'''["']orgUnitDataGuid["']\s*:\s*["']([^"]+)["']''', dispo_resp.text)
                
                discovered_guids = list(set(guids))
                if discovered_guids:
                    self.org_unit_data_guid = discovered_guids[-1]
                    for g in discovered_guids:
                        if g not in self.extra_guids: self.extra_guids.append(g)
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
                                if g: 
                                    for found_g in g:
                                        if found_g not in self.extra_guids: self.extra_guids.append(found_g)
                                    self.org_unit_data_guid = g[-1]
                            except Exception: pass
                        if self.header_key: break
                return True, "Eingeloggt."
            except Exception as e: return False, f"Fehler: {e}"

    def _get_api_headers(self) -> Dict[str, str]:
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest', 'User-Agent': self.user_agent}
        if self.header_key and self.header_value: headers[self.header_key] = self.header_value
        return headers

    def _fix_datetime(self, s: Optional[str]) -> Optional[datetime]:
        if not s: return None
        try:
            dt = datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
            offset = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
            return dt + timedelta(seconds=offset)
        except: return None

    def get_project_guids(self) -> Dict[str, str]:
        """Fetches available project GUIDs and Names from the projects page."""
        r_proj = self.session.get(f"{self.base_url}/StaffPortal/projects.php", headers=self._get_api_headers())
        guid_pattern = r'([a-f0-9]{40}(?:_\d+)+)'
        all_raw = set(re.findall(guid_pattern, r_proj.text))
        if self.org_unit_data_guid: all_raw.add(self.org_unit_data_guid)
        if self.extra_guids: all_raw.update(self.extra_guids)
        guids_to_try = list(all_raw) or [DEFAULT_GUID]
        project_map = {}
        try:
            resp = self.session.post(f"{self.base_url}/StaffPortal/projects/show.content.projects.php", headers=self._get_api_headers(), data={'orgUnitDataGuid[]': guids_to_try, 'projectType': '', 'name': '', 'month': '', 'form.event.onsubmit': 'searchForm'})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
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
                for g in re.findall(guid_pattern, resp.text):
                    if g not in project_map and g not in guids_to_try: project_map[g] = "Event"
        except: pass
        return project_map

    def load_events_plan(self, date_from: datetime = None, date_to: datetime = None) -> List[Dict[str, Any]]:
        """Loads roster for events by parsing HTML cards and augmenting with JSON data."""
        project_map = self.get_project_guids()
        guids_to_try = [self.org_unit_data_guid] + self.extra_guids
        try:
            resp = self.session.post(f"{self.base_url}/StaffPortal/projects/show.content.projects.php", headers=self._get_api_headers(), data={'orgUnitDataGuid[]': guids_to_try, 'projectType': '', 'name': '', 'month': '', 'form.event.onsubmit': 'searchForm'})
            if resp.status_code == 200:
                events, soup = [], BeautifulSoup(resp.text, 'html.parser')
                for card in soup.find_all('div', attrs={'data-role': 'incode-project'}):
                    guid, b_s, e_s = card.get('data-dataguid'), card.get('data-begin'), card.get('data-end')
                    if not guid or not b_s: continue
                    b_dt, e_dt = self._fix_datetime(b_s), self._fix_datetime(e_s)
                    if not b_dt: continue
                    t_tag = card.find('h3', class_='card-title')
                    events.append({'guid': guid, 'begin': b_dt, 'end': e_dt, 'vehicle': t_tag.get_text(strip=True) if t_tag else "Event", 'location': '', 'crew': {}, 'open_slots': 0})
                if events:
                    start, end = min(e['begin'] for e in events), max(e['end'] for e in events)
                    guids = list(set([e['guid'] for e in events]))
                    main_org = self.org_unit_data_guid or (self.extra_guids[0] if self.extra_guids else DEFAULT_GUID)
                    for i in range(0, len(guids), 30):
                        r = self.session.post(f"{self.base_url}/StaffPortal/plan/data/loadProjectsPlan.json", headers=self._get_api_headers(), data={'orgUnitDataGuid': main_org, 'withSubOrgUnits': '1', 'sortPlan': 'false', 'dateFrom': start.strftime('%Y-%m-%dT00:00:00.000Z'), 'dateTo': end.strftime('%Y-%m-%dT23:59:59.000Z'), 'projectDataGuids[]': guids[i:i+30]})
                        if r.status_code == 200:
                            data = r.json()
                            it = data.get('data', {}).values() if isinstance(data.get('data'), dict) else data.get('data', [])
                            for item in it:
                                if not isinstance(item, dict): continue
                                pg, cb = item.get('projectDataGuid'), self._fix_datetime(item.get('begin'))
                                if not pg or not cb: continue
                                for e in events:
                                    if e['guid'] == pg and e['begin'].date() == cb.date():
                                        infos = item.get('additionalInfos', {})
                                        rn, pn, loc = str(infos.get('ressource_name', '')).strip(), str(infos.get('project_name', '')).strip(), str(item.get('orgUnitName', '')).strip()
                                        if pn and (e['vehicle'] == "Event" or len(pn) > len(e['vehicle'])): e['vehicle'] = pn
                                        if loc: e['location'] = loc
                                        eid = str(item.get('externalId', '')).upper()
                                        if not rn or rn == '*':
                                            if eid != "KFZ": e['open_slots'] += 1
                                        elif eid != "KFZ": e['crew'][f"{eid or 'Staff'}_{len(e['crew'])}"] = rn
                return events
        except: pass
        return []

    def load_my_event_duties(self) -> List[Dict[str, Any]]:
        df, dt = datetime.now().strftime('%Y-%m-%dT00:00:00.000Z'), (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%dT23:59:59.000Z')
        try:
            resp = self.session.post(f"{self.base_url}/StaffPortal/duties/data/loadInRange.json", headers=self._get_api_headers(), data={'orgUnitDataGuid': self.org_unit_data_guid or DEFAULT_GUID, 'withSubOrgUnits': '0', 'dateFrom': df, 'dateTo': dt, 'forEvents': 'true', 'loadDutiesForAllRessources': '0'})
            if resp.status_code == 200: return self._parse_personal_duties(resp.json(), filter_mode='include_all')
        except: pass
        return []

    def _calculate_staff_score(self, p: Dict[str, Any]) -> int:
        score = 0
        if p.get('telefon'): score += 10
        if p.get('email'): score += 10
        if p.get('ressourceToOccupations'): score += 5 * len(p.get('ressourceToOccupations', []))
        if p.get('maportal_role') and p.get('maportal_role') != 'dutytype_active': score += 5
        score += len(str(p.get('_display_name', '')))
        return score

    def search_staff_contact(self, query_name: str) -> List[Dict[str, str]]:
        now = datetime.now()
        df, dt = (now - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00.000Z'), (now + timedelta(days=365)).strftime('%Y-%m-%dT23:59:59.000Z')
        
        guids = set()
        if self.org_unit_data_guid: guids.add(self.org_unit_data_guid)
        if self.extra_guids: guids.update(self.extra_guids)
        guids.add(DEFAULT_GUID)
        
        sorted_guids = sorted([g for g in guids if g])
        
        # Intermediate storage for merging
        pnr_to_best_record = {}
        name_to_pnr = {}
        name_no_pnr_to_best_record = {}
        
        for guid in sorted_guids:
            try:
                resp = self.session.post(f"{self.base_url}/StaffPortal/staff/data/getStaff.json", headers=self._get_api_headers(), data={'orgUnitDataGuid': guid, 'withSubOrgUnits': 'true', 'loadModelData': '1', 'dateFrom': df, 'dateTo': dt})
                if resp.status_code == 200: 
                    found = self._parse_staff_contact(resp.json(), query_name)
                    for p in found:
                        name = p.get('_display_name')
                        pnr = p.get('personalnummer')
                        score = self._calculate_staff_score(p)
                        p['_score'] = score
                        
                        if pnr:
                            # We have a PNR. 
                            name_to_pnr[name] = pnr
                            if pnr not in pnr_to_best_record or score > pnr_to_best_record[pnr].get('_score', 0):
                                pnr_to_best_record[pnr] = p
                            # If we previously had this person as name-only, they will be cleaned up in the final step
                        else:
                            # No PNR. Check if we already know a PNR for this name
                            known_pnr = name_to_pnr.get(name)
                            if known_pnr:
                                # Merge with the PNR record
                                if score > pnr_to_best_record[known_pnr].get('_score', 0):
                                    # Update info but keep the PNR from the existing best
                                    p['personalnummer'] = known_pnr
                                    pnr_to_best_record[known_pnr] = p
                            else:
                                # Truly no PNR yet. Store by name
                                if name not in name_no_pnr_to_best_record or score > name_no_pnr_to_best_record[name].get('_score', 0):
                                    name_no_pnr_to_best_record[name] = p
            except: pass
            
        # Final aggregation: records with PNR + records with NO PNR that aren't duplicates
        results_map = {**pnr_to_best_record}
        for name, record in name_no_pnr_to_best_record.items():
            if name not in name_to_pnr: # Don't add if we now have a PNR version
                results_map[f"no_pnr_{name}"] = record
                
        results = list(results_map.values())
        results.sort(key=lambda x: x.get('_display_name', ''))
        return results

    def _parse_staff_contact(self, data: Dict[str, Any], query_name: str) -> List[Dict[str, Any]]:
        results, staff_list, q = [], data.get('data', []), query_name.lower()
        for p in staff_list:
            full_name = f"{str(p.get('vorname', '')).strip()} {str(p.get('nachname', '')).strip()}".strip() or str(p.get('name', '')).strip()
            search_text = (full_name + str(p.get('personalnummer', '')) + str(p.get('email', ''))).lower()
            for occ in p.get('ressourceToOccupations', []): search_text += (str(occ.get('name', '')) + str(occ.get('externalId', '')) + str(occ.get('ressourceIndicator', ''))).lower()
            if q in search_text: p['_display_name'] = full_name; results.append(p)
        results.sort(key=lambda x: x.get('_display_name', ''))
        return results

    def _extract_role(self, person_data: Dict[str, Any]) -> str:
        roles = [occ.get('name', '') for occ in person_data.get('ressourceToOccupations', []) if occ.get('name')]
        return ", ".join(roles) if roles else "-"

    def load_absences(self) -> List[Dict[str, Any]]:
        results, daily_map, now = [], {}, datetime.now()
        start_date, end_date = now - timedelta(days=30), now + timedelta(days=400)
        df_str, dt_str = start_date.strftime('%Y-%m-%dT00:00:00.000Z'), end_date.strftime('%Y-%m-%dT23:59:59.000Z')
        def norm_start(dt): return (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0) if dt.hour >= 20 else dt
        holiday_cache = {}
        def is_h(d):
            if d.year not in holiday_cache: holiday_cache[d.year] = self._get_holidays(d.year)
            return d in holiday_cache[d.year]
        
        # v1.7 style body (no orgUnitDataGuid)
        body = {'max': '1000', 'dateFrom': df_str, 'dateTo': dt_str, 'reason': '', 'form.event.onsubmit': 'searchForm'}
        
        try:
            resp = self.session.post(f"{self.base_url}/StaffPortal/absence/data/load.json", headers=self._get_api_headers(), data=body)
            if resp.status_code == 200:
                for item in resp.json().get('data', []):
                    reason = item.get('reasonName') or item.get('absenceTypeName') or "Abwesend"
                    b, e = norm_start(self._fix_datetime(item.get('begin'))), self._fix_datetime(item.get('end'))
                    if not b or not e: continue
                    if e.hour == 0 and e.minute == 0: e -= timedelta(seconds=1)
                    curr = b.date()
                    while curr <= e.date():
                        lbl = reason
                        # Rule: Holidays are 'Geplante Sonderabwesenheit', but if they fall on a Sunday, they are just 'Abwesend'
                        if is_h(curr):
                            lbl = "Abwesend" if curr.weekday() == 6 else "Geplante Sonderabwesenheit"
                        
                        # Priority: Holidays and actual absences over general weekend markers
                        if curr not in daily_map or is_h(curr) or any(w in lbl.lower() for w in ["urlaub", "abwesend", "krank"]):
                            daily_map[curr] = {'label': lbl, 'fixed': True}
                        curr += timedelta(days=1)
        except: pass
        try:
            resp = self.session.post(f"{self.base_url}/StaffPortal/absence/data/loadWishes.json", headers=self._get_api_headers(), data=body)
            if resp.status_code == 200:
                for item in resp.json().get('data', []):
                    try: state = int(item.get('approvalState'))
                    except: state = 0
                    # state 0 = requested, state 1 = approved
                    if state not in [0, 1] or item.get('withdrawn') in [1, True]: continue
                    
                    reason = item.get('reasonName') or item.get('absenceTypeName') or "Abwesend"
                    status_text = " [yellow](Beantragt)[/yellow]" if state == 0 else " [green](Gen. / n. eingetr.)[/green]"
                    
                    b, e = norm_start(self._fix_datetime(item.get('begin'))), self._fix_datetime(item.get('end'))
                    if not b or not e: continue
                    if e.hour == 0 and e.minute == 0: e -= timedelta(seconds=1)
                    curr = b.date()
                    while curr <= e.date():
                        if curr not in daily_map or not daily_map[curr]['fixed']:
                            lbl = reason
                            if is_h(curr):
                                lbl = "Abwesend" if curr.weekday() == 6 else "Geplante Sonderabwesenheit"
                            
                            if curr not in daily_map or is_h(curr) or "urlaub" in lbl.lower():
                                daily_map[curr] = {'label': lbl + status_text, 'fixed': False}
                        curr += timedelta(days=1)
        except: pass
        
        # Weekend / Sunday Logic
        sorted_d = sorted(daily_map.keys())
        # 1. Sunday BEFORE vacation/holiday block (if starts on Monday)
        for d in sorted_d:
            if d.weekday() == 0:
                lbl_mon = daily_map[d]['label'].lower()
                if "urlaub" in lbl_mon or "sonderabwesenheit" in lbl_mon:
                    prev_sun = d - timedelta(days=1)
                    prev_fri = d - timedelta(days=3)
                    
                    # Check if Friday was also Urlaub (Continuous vacation)
                    is_connecting = False
                    if prev_fri in daily_map:
                        lbl_fri = daily_map[prev_fri]['label'].lower()
                        if "urlaub" in lbl_fri or "sonderabwesenheit" in lbl_fri:
                            is_connecting = True
                    
                    if is_connecting:
                        # Connecting weekend -> Should be Abwesend
                        if prev_sun not in daily_map or daily_map[prev_sun]['label'] == "Freies Wochenende":
                            daily_map[prev_sun] = {'label': "Abwesend", 'fixed': False}
                    else:
                        # Start of vacation -> Pre-vacation Sunday is Free
                        # Use 'Freies Wochenende' even if it was previously marked as 'Abwesend'
                        if prev_sun not in daily_map or daily_map[prev_sun]['label'] == "Abwesend":
                            daily_map[prev_sun] = {'label': "Freies Wochenende", 'fixed': False}
        
        # 2. Sunday AFTER vacation (if vacation ends on/covers Saturday) -> Abwesend
        # Refresh sorted list after potential additions
        sorted_d = sorted(daily_map.keys())
        for d in sorted_d:
            if d.weekday() == 5 and "urlaub" in daily_map[d]['label'].lower():
                sun = d + timedelta(days=1)
                if sun not in daily_map:
                    suffix = ""
                    if "[yellow]" in daily_map[d]['label']: suffix = " [yellow](Beantragt)[/yellow]"
                    elif "[green]" in daily_map[d]['label']: suffix = " [green](Gen. / n. eingetr.)[/green]"
                    daily_map[sun] = {'label': "Abwesend" + suffix, 'fixed': False}
                    
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

    def _get_holidays(self, year: int) -> List[datetime.date]:
        holidays = [
            datetime(year, 1, 1).date(), datetime(year, 1, 6).date(), 
            datetime(year, 5, 1).date(), datetime(year, 8, 15).date(), 
            datetime(year, 10, 10).date(), datetime(year, 10, 26).date(), 
            datetime(year, 11, 1).date(), datetime(year, 12, 8).date(), 
            datetime(year, 12, 24).date(), datetime(year, 12, 25).date(), 
            datetime(year, 12, 26).date(), datetime(year, 12, 31).date()
        ]
        a, b, c = year % 19, year // 100, year % 100
        d, e, f = b // 4, b % 4, (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = c // 4, c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        mo, dy = (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1
        easter = datetime(year, mo, dy).date()
        # Ostersonntag (0), Ostermontag (+1), Himmelfahrt (+39), Pfingstsonntag (+49), Pfingstmontag (+50), Fronleichnam (+60)
        holidays.extend([
            easter, easter + timedelta(days=1), 
            easter + timedelta(days=39), easter + timedelta(days=49), 
            easter + timedelta(days=50), easter + timedelta(days=60)
        ])
        return holidays

    def load_archive_duties(self, year: int, filter_mode: str = 'exclude_absences') -> List[Dict[str, Any]]:
        try:
            resp = self.session.post(f"{self.base_url}/StaffPortal/archive/data/loadDuties.json", headers=self._get_api_headers(), data={'year': str(year), 'month': '', 'dateDescendingSort': 'true', 'orgUnit': '', 'withSubOrgs': 'on', 'form.event.onsubmit': 'searchForm'})
            if resp.status_code == 200: return self._parse_personal_duties(resp.json(), filter_mode)
        except: pass
        return []

    def load_future_duties(self, use_cache=True, filter_mode: str = 'exclude_absences') -> List[Dict[str, Any]]:
        cache_key = f"future_duties_{filter_mode}"
        if use_cache:
            cached = self._get_cached_data(cache_key)
            if cached: return cached
        now = datetime.now()
        start_fetch = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        next_month = now.replace(year=now.year + 1, month=1, day=1) if now.month == 12 else now.replace(month=now.month + 1, day=1)
        nm_end = next_month.replace(year=next_month.year + 1, month=1, day=1) - timedelta(seconds=1) if next_month.month == 12 else next_month.replace(month=next_month.month + 1, day=1) - timedelta(seconds=1)
        ts_s, ts_e = int(start_fetch.timestamp()), int(nm_end.timestamp())
        try:
            resp = self.session.post(f"{self.base_url}/StaffPortal/duties/data/load.json", headers=self._get_api_headers(), data={'max': '1000', 'dateFrom': start_fetch.strftime('%Y-%m-%dT00:00:00.000Z'), 'dateTo': nm_end.strftime('%Y-%m-%dT23:59:59.000Z'), 'from': str(ts_s), 'to': str(ts_e), 'start': str(ts_s), 'end': str(ts_e), 'includeFinished': '1', 'view': 'month'})
            resp.raise_for_status()
            duties = self._parse_personal_duties(resp.json(), filter_mode)
            archive = self.load_archive_duties(now.year, filter_mode)
            d_map = {d['begin']: d for d in duties}
            for ad in archive:
                if ad['begin'] not in d_map: d_map[ad['begin']] = ad
                elif not d_map[ad['begin']].get('location') and ad.get('location'): d_map[ad['begin']] = ad
            duties = sorted(d_map.values(), key=lambda x: x['begin'])
            self._set_cached_data(cache_key, duties)
            return duties
        except:
            if cache_key in self.cache: return self.cache[cache_key]['data']
            return []

    def load_daily_plan(self, date: datetime, use_cache=True) -> List[Dict[str, Any]]:
        cache_key = f"daily_{date.strftime('%Y-%m-%d')}"
        if use_cache:
            cached = self._get_cached_data(cache_key)
            if cached: return self._rehydrate_cache(cached)
        sd, ed = date.replace(hour=0, minute=0, second=0, microsecond=0), date.replace(hour=23, minute=59, second=59, microsecond=999999)
        try:
            results = self._fetch_daily_plan_items(sd, ed)
            serializable = [{'begin': i['begin'].strftime('%Y-%m-%dT%H:%M:%S') if isinstance(i.get('begin'), datetime) else i.get('begin'), 'end': i['end'].strftime('%Y-%m-%dT%H:%M:%S') if isinstance(i.get('end'), datetime) else i.get('end'), 'vehicle': i['vehicle'], 'crew': i['crew']} for i in results]
            self._set_cached_data(cache_key, serializable)
            return results
        except:
            if cache_key in self.cache: return self._rehydrate_cache(self.cache[cache_key]['data'])
            return []

    def _rehydrate_cache(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        hydrated = []
        for item in data:
            ni = item.copy()
            if isinstance(ni.get('begin'), str): ni['begin'] = datetime.strptime(ni['begin'], '%Y-%m-%dT%H:%M:%S')
            if isinstance(ni.get('end'), str): ni['end'] = datetime.strptime(ni['end'], '%Y-%m-%dT%H:%M:%S')
            hydrated.append(ni)
        return hydrated

    def _parse_personal_duties(self, data: Dict[str, Any], filter_mode: str = 'exclude_absences') -> List[Dict[str, Any]]:
        results, fw = [], ["urlaub", "frei", "wunsch", "abwesenheit", "abwesend", "pflege", "krank", "zeitausgleich", "sonderabwesenheit", "ersatzruhe", "ruhetag", "seminar", "fortbildung", "schulung", "dienstfrei", "ausbildung", "lehrgang"]
        for item in data.get('data', []):
            if not isinstance(item, dict): continue
            dt_name = str(item.get('dutyTypeName') or item.get('absenceTypeName') or item.get('type') or item.get('text') or "")
            loc, comm = str(item.get('orgUnitName', '')), str(item.get('comment', ''))
            alloc = item.get('allocationInfo', {})
            al = next(iter(alloc.values())) if isinstance(alloc, dict) and alloc.values() else (alloc if isinstance(alloc, list) else [])
            content = (dt_name + loc + comm + str(al)).lower()
            is_abs = bool(item.get('absenceTypeName')) or any(w in content for w in fw)
            if filter_mode == 'exclude_absences' and is_abs: continue
            if filter_mode == 'only_absences' and not is_abs: continue
            b, e = self._fix_datetime(item.get('begin')), self._fix_datetime(item.get('end'))
            if not b or not e: continue
            veh, crew = "", []
            if len(al) > 1:
                last = str(al[-1])
                if last and (last[0].isdigit() or any(vt in last.upper() for vt in ["RTW", "KTW", "BTW", "NEF", "BKTW", "VEF"])): veh, crew = last, [str(x) for x in al[1:-1]]
                else: veh, crew = "", [str(x) for x in al[1:]]
            results.append({'begin': b.strftime('%Y-%m-%dT%H:%M:%S'), 'end': e.strftime('%Y-%m-%dT%H:%M:%S'), 'location': loc, 'vehicle': veh, 'duty_type': dt_name, 'crew': crew})
        return results

    def _parse_daily_plan_raw(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        grouped, it = {}, data.get('data', {}).values() if isinstance(data.get('data'), dict) else data.get('data', [])
        for i in it:
            pg = i.get('parentDataGuid')
            if not pg: continue
            if pg not in grouped: grouped[pg] = {"crew": {}, "vehicle": "", "begin": None, "end": None}
            eid, rn = str(i.get('externalId', '')).upper(), str(i.get('additionalInfos', {}).get('ressource_name', '')).strip()
            b, e = self._fix_datetime(i.get('begin')), self._fix_datetime(i.get('end'))
            if eid == "KFZ": grouped[pg]["vehicle"], grouped[pg]["begin"], grouped[pg]["end"] = rn, b, e
            elif eid in ["FAHRER", "SANITAETER1", "SANITAETER2"] and rn:
                grouped[pg]["crew"][eid] = rn
                if not grouped[pg]["begin"]: grouped[pg]["begin"], grouped[pg]["end"] = b, e
        return [v for v in grouped.values() if v["begin"] and v["end"]]

    def _fetch_daily_plan_items(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        df, dt = (date_from - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z'), (date_to + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
        guids = list(set([self.org_unit_data_guid] + self.extra_guids + [DEFAULT_GUID]))
        try:
            d_resp = self.session.post(f"{self.base_url}/StaffPortal/duties/data/load.json", headers=self._get_api_headers(), data={'max': '20'})
            if d_resp.status_code == 200:
                for item in d_resp.json().get('data', []):
                    og = item.get('orgUnitDataGuid')
                    if og and og not in guids: guids.append(og)
        except: pass
        results, seen = [], set()
        for g in [x for x in guids if x]:
            try:
                r = self.session.post(f"{self.base_url}/StaffPortal/plan/data/loadPlan.json", headers=self._get_api_headers(), data={'orgUnitDataGuid': g, 'withSubOrgUnits': '1', 'dateFrom': df, 'dateTo': dt, 'sortPlan': 'false'})
                if r.status_code == 200:
                    data = r.json()
                    if data.get('data'):
                        for item in self._parse_daily_plan_raw(data):
                            if item['begin'] and item['end'] and not (item['end'] < date_from or item['begin'] > date_to):
                                sig = (item['vehicle'], item['begin'], item['end'], tuple(sorted(item['crew'].items())))
                                if sig not in seen: seen.add(sig); results.append(item)
            except: continue
        return results