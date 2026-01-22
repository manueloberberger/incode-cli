import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.models import Duty

def fix_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s: return None
    try:
        dt = datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
        offset = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
        return dt + timedelta(seconds=offset)
    except: return None

def calculate_staff_score(p: Dict[str, Any]) -> int:
    score = 0
    if p.get('telefon'): score += 10
    if p.get('email'): score += 10
    if p.get('ressourceToOccupations'): score += 5 * len(p.get('ressourceToOccupations', []))
    if p.get('maportal_role') and p.get('maportal_role') != 'dutytype_active': score += 5
    score += len(str(p.get('_display_name', '')))
    return score

def parse_staff_contact(data: Dict[str, Any], query_name: str) -> List[Dict[str, Any]]:
    results, staff_list, q = [], data.get('data', []), query_name.lower()
    
    count_with_pnr = 0
    for p in staff_list:
        full_name = f"{str(p.get('vorname', '')).strip()} {str(p.get('nachname', '')).strip()}".strip() or str(p.get('name', '')).strip()
        pnr = str(p.get('personalnummer', ''))
        if pnr: count_with_pnr += 1
        
        # Build comprehensive search text
        search_text = (full_name + pnr + str(p.get('email', ''))).lower()
        # Add extra contact fields to search
        for k in ['telefon', 'telefon_privat', 'handy', 'mobile', 'email_privat']:
            val = p.get(k)
            if val: search_text += str(val).lower()
        
        for occ in p.get('ressourceToOccupations', []): search_text += (str(occ.get('name', '')) + str(occ.get('externalId', '')) + str(occ.get('ressourceIndicator', ''))).lower()
        
        if q in search_text: 
            p['_display_name'] = full_name
            results.append(p)
    
    results.sort(key=lambda x: x.get('_display_name', ''))
    return results

def extract_role(person_data: Dict[str, Any]) -> str:
    roles = [occ.get('name', '') for occ in person_data.get('ressourceToOccupations', []) if occ.get('name')]
    return ", ".join(roles) if roles else "-"

def parse_personal_duties(data: Dict[str, Any], filter_mode: str = 'exclude_absences') -> List[Duty]:
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
        b, e = fix_datetime(item.get('begin')), fix_datetime(item.get('end'))
        if not b or not e: continue
        veh, crew = "", []
        if len(al) > 1:
            last = str(al[-1])
            if last and (last[0].isdigit() or any(vt in last.upper() for vt in ["RTW", "KTW", "BTW", "NEF", "BKTW", "VEF"])): veh, crew = last, [str(x) for x in al[1:-1]]
            else: veh, crew = "", [str(x) for x in al[1:]]
        
        # Create Duty Object
        results.append(Duty(
            begin=b,
            end=e,
            location=loc,
            vehicle=veh,
            duty_type=dt_name,
            crew=crew,
            comment=comm
        ))
    return results

def parse_daily_plan_raw(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    grouped, it = {}, data.get('data', {}).values() if isinstance(data.get('data'), dict) else data.get('data', [])
    for i in it:
        pg = i.get('parentDataGuid')
        if not pg: continue
        if pg not in grouped: grouped[pg] = {"crew": {}, "vehicle": "", "begin": None, "end": None}
        # Explicit cast for type checkers
        entry: Dict[str, Any] = grouped[pg]
        eid, rn = str(i.get('externalId', '')).upper(), str(i.get('additionalInfos', {}).get('ressource_name', '')).strip()
        b, e = fix_datetime(i.get('begin')), fix_datetime(i.get('end'))
        if eid == "KFZ": entry["vehicle"], entry["begin"], entry["end"] = rn, b, e
        elif eid in ["FAHRER", "SANITAETER1", "SANITAETER2"] and rn:
            entry["crew"][eid] = rn
            if not entry["begin"]: entry["begin"], entry["end"] = b, e
    return [v for v in grouped.values() if v["begin"] and v["end"]]
