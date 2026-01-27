"""
API response parsing utilities for incode-cli.

This module provides functions to parse and transform raw API responses
from the Incode duty roster system into structured Python objects.
"""
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.models import Duty
from src.config import VEHICLE_INDICATORS


def fix_datetime(s: Optional[str]) -> Optional[datetime]:
    """
    Parse an ISO datetime string and adjust for local timezone.
    
    Args:
        s: ISO format datetime string (e.g., '2024-01-15T08:00:00.000Z').
        
    Returns:
        Datetime object adjusted to local timezone, or None if parsing fails.
    """
    if not s: 
        return None
    try:
        dt = datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
        offset = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
        return dt + timedelta(seconds=offset)
    except (ValueError, IndexError):
        return None


def calculate_staff_score(p: Dict[str, Any]) -> int:
    """
    Calculate a relevance score for a staff member.
    
    Used for sorting search results by completeness of contact information.
    Higher scores indicate more complete/relevant records.
    
    Args:
        p: Staff member data dictionary from API.
        
    Returns:
        Integer score (higher = more relevant).
    """
    score = 0
    if p.get('telefon'): 
        score += 10
    if p.get('email'): 
        score += 10
    if p.get('ressourceToOccupations'): 
        score += 5 * len(p.get('ressourceToOccupations', []))
    if p.get('maportal_role') and p.get('maportal_role') != 'dutytype_active': 
        score += 5
    score += len(str(p.get('_display_name', '')))
    return score


def parse_staff_contact(data: Dict[str, Any], query_name: str) -> List[Dict[str, Any]]:
    """
    Parse and filter staff contact data from API response.
    
    Searches through staff data and returns matching entries based on the query.
    Matches against name, personnel number, email, and phone fields.
    
    Args:
        data: Raw API response containing staff list.
        query_name: Search query string (case-insensitive).
        
    Returns:
        List of matching staff dictionaries, sorted by display name.
    """
    results: List[Dict[str, Any]] = []
    staff_list = data.get('data', [])
    q = query_name.lower()
    
    for p in staff_list:
        full_name = f"{str(p.get('vorname', '')).strip()} {str(p.get('nachname', '')).strip()}".strip() or str(p.get('name', '')).strip()
        pnr = str(p.get('personalnummer', ''))
        
        # Build comprehensive search text
        search_text = (full_name + pnr + str(p.get('email', ''))).lower()
        
        # Add extra contact fields to search
        for k in ['telefon', 'telefon_privat', 'handy', 'mobile', 'email_privat']:
            val = p.get(k)
            if val: 
                search_text += str(val).lower()
        
        # Add occupation/role info to search
        for occ in p.get('ressourceToOccupations', []): 
            search_text += (str(occ.get('name', '')) + str(occ.get('externalId', '')) + str(occ.get('ressourceIndicator', ''))).lower()
        
        if q in search_text: 
            p['_display_name'] = full_name
            results.append(p)
    
    results.sort(key=lambda x: x.get('_display_name', ''))
    return results


def extract_role(person_data: Dict[str, Any]) -> str:
    """
    Extract role/occupation string from person data.
    
    Args:
        person_data: Staff member data dictionary.
        
    Returns:
        Comma-separated role names, or '-' if no roles found.
    """
    roles = [occ.get('name', '') for occ in person_data.get('ressourceToOccupations', []) if occ.get('name')]
    return ", ".join(roles) if roles else "-"


def parse_personal_duties(data: Dict[str, Any], filter_mode: str = 'exclude_absences', my_name: Optional[str] = None) -> List[Duty]:
    """
    Parse duty/shift data from API response into Duty objects.
    
    Handles various duty formats and filters based on mode. When my_name is provided,
    reorders crew list to show the current user first.
    
    Args:
        data: Raw API response containing duty data.
        filter_mode: One of 'exclude_absences', 'only_absences', or 'include_all'.
        my_name: Current user's name for crew list reordering.
        
    Returns:
        List of Duty objects parsed from the response.
    """
    results: List[Duty] = []
    
    # Keywords that indicate an absence rather than a duty
    absence_keywords = [
        "urlaub", "wunsch", "abwesenheit", "abwesend", "pflege", "krank", 
        "zeitausgleich", "sonderabwesenheit", "ersatzruhe", "ruhetag", 
        "seminar", "fortbildung", "schulung", "dienstfrei", "ausbildung", "lehrgang"
    ]
    
    for item in data.get('data', []):
        if not isinstance(item, dict): 
            continue
            
        dt_name = str(item.get('dutyTypeName') or item.get('absenceTypeName') or item.get('type') or item.get('text') or "")
        loc = str(item.get('orgUnitName', ''))
        comm = str(item.get('comment', ''))
        alloc = item.get('allocationInfo', {})
        al = next(iter(alloc.values())) if isinstance(alloc, dict) and alloc.values() else (alloc if isinstance(alloc, list) else [])
        content = (dt_name + loc + comm + str(al)).lower()
        is_abs = bool(item.get('absenceTypeName')) or any(w in content for w in absence_keywords)
        
        # Apply filter
        if filter_mode == 'exclude_absences' and is_abs: 
            continue
        if filter_mode == 'only_absences' and not is_abs: 
            continue
            
        b, e = fix_datetime(item.get('begin')), fix_datetime(item.get('end'))
        if not b or not e: 
            continue

        # Parse vehicle and crew from allocation info
        veh, crew = "", []
        if len(al) > 1:
            last = str(al[-1])
            if last and (last[0].isdigit() or any(vt in last.upper() for vt in VEHICLE_INDICATORS)):
                veh, crew = last, [str(x) for x in al[1:-1]]
            else:
                veh, crew = "", [str(x) for x in al[1:]]

        # Reorder crew to show current user first (optimized with max())
        if my_name and crew:
            my_parts = [p for p in my_name.lower().replace(',', '').split() if len(p) > 2]

            def match_score(member: str) -> int:
                n_lower = member.lower()
                return sum(1 for part in my_parts if part in n_lower)

            # Find best match using max() - O(n) instead of manual loop
            if crew:
                best_idx, best_member = max(
                    enumerate(crew),
                    key=lambda x: match_score(x[1])
                )
                best_score = match_score(best_member)
                
                if best_score > 0:
                    me = crew.pop(best_idx)
                    crew.insert(0, me)

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
    """
    Parse daily plan data into grouped shift entries.
    
    Groups plan items by parentDataGuid to combine vehicle and crew
    assignments into single shift entries.
    
    Args:
        data: Raw API response from loadPlan endpoint.
        
    Returns:
        List of shift dictionaries with 'crew', 'vehicle', 'begin', 'end' keys.
    """
    grouped: Dict[str, Dict[str, Any]] = {}
    items = data.get('data', {}).values() if isinstance(data.get('data'), dict) else data.get('data', [])
    
    for i in items:
        pg = i.get('parentDataGuid')
        if not pg: 
            continue
            
        if pg not in grouped: 
            grouped[pg] = {"crew": {}, "vehicle": "", "begin": None, "end": None}
            
        entry: Dict[str, Any] = grouped[pg]
        eid = str(i.get('externalId', '')).upper()
        rn = str(i.get('additionalInfos', {}).get('ressource_name', '')).strip()
        b, e = fix_datetime(i.get('begin')), fix_datetime(i.get('end'))
        
        if eid == "KFZ": 
            entry["vehicle"], entry["begin"], entry["end"] = rn, b, e
        elif eid in ["FAHRER", "SANITAETER1", "SANITAETER2"] and rn:
            entry["crew"][eid] = rn
            if not entry["begin"]: 
                entry["begin"], entry["end"] = b, e
                
    return [v for v in grouped.values() if v["begin"] and v["end"]]
