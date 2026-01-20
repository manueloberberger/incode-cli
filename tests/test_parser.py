import pytest
from datetime import datetime
from src.parser import (
    fix_datetime,
    calculate_staff_score,
    extract_role,
    parse_staff_contact,
    parse_personal_duties,
    parse_daily_plan_raw
)
from src.models import Duty

def test_fix_datetime():
    # Test valid input
    dt_str = "2026-05-10T15:30:00"
    dt = fix_datetime(dt_str)
    assert dt is not None
    # We check if it returns a datetime object.
    # The timezone offset logic depends on local system time, so checking exact hour might be flaky if we assume specific timezone.
    # However, we can check basic properties.
    assert dt.minute == 30
    assert dt.second == 0
    
    # Test None
    assert fix_datetime(None) is None
    
    # Test Invalid
    assert fix_datetime("invalid-date-string") is None

def test_calculate_staff_score():
    p1 = {"_display_name": "Short", "telefon": "123"}
    p2 = {"_display_name": "Longer Name", "email": "a@b.c", "ressourceToOccupations": [1, 2]}
    
    score1 = calculate_staff_score(p1) # 5 (len) + 10 (tel) = 15
    score2 = calculate_staff_score(p2) # 11 (len) + 10 (email) + 10 (2*5 occ) = 31
    
    assert score2 > score1

def test_extract_role():
    p1 = {"ressourceToOccupations": [{"name": "Sanitäter"}, {"name": "Fahrer"}]}
    assert extract_role(p1) == "Sanitäter, Fahrer"
    
    p2 = {}
    assert extract_role(p2) == "-"

def test_parse_staff_contact():
    data = {"data": [
        {"vorname": "Max", "nachname": "Mustermann", "personalnummer": "100", "email": "max@example.com"},
        {"vorname": "Julia", "nachname": "Musterfrau", "personalnummer": "101", "email": "julia@example.com"},
        {"name": "OnlyName", "personalnummer": "102"}
    ]}
    
    # Search by name match
    res = parse_staff_contact(data, "Muster")
    assert len(res) == 2
    assert res[0]["_display_name"] == "Julia Musterfrau" # Sorted alphabetically
    assert res[1]["_display_name"] == "Max Mustermann"
    
    # Search by PNR
    res_pnr = parse_staff_contact(data, "102")
    assert len(res_pnr) == 1
    assert res_pnr[0]["_display_name"] == "OnlyName"
    
    # No match
    res_none = parse_staff_contact(data, "NonExistent")
    assert len(res_none) == 0

def test_parse_personal_duties():
    data = {
        "data": [
            {
                "dutyTypeName": "Tagdienst",
                "orgUnitName": "Station 1",
                "begin": "2026-01-01T06:00:00",
                "end": "2026-01-01T18:00:00",
                "allocationInfo": ["Max", "Julia", "RTW 1"]
            },
            {
                "absenceTypeName": "Urlaub",
                "begin": "2026-01-02T00:00:00",
                "end": "2026-01-02T23:59:59"
            }
        ]
    }
    
    # Filter: exclude_absences (Default)
    duties = parse_personal_duties(data)
    assert len(duties) == 1
    assert duties[0].duty_type == "Tagdienst"
    assert duties[0].vehicle == "RTW 1"
    
    # Filter: include_all
    all_duties = parse_personal_duties(data, filter_mode="include_all")
    assert len(all_duties) == 2
    
    # Filter: only_absences
    absences = parse_personal_duties(data, filter_mode="only_absences")
    assert len(absences) == 1
    assert absences[0].duty_type == "Urlaub"

def test_parse_daily_plan_raw():
    data = {
        "data": {
            "item1": {
                "parentDataGuid": "group1",
                "externalId": "KFZ",
                "additionalInfos": {"ressource_name": "RTW 1"},
                "begin": "2026-01-01T07:00:00",
                "end": "2026-01-01T19:00:00"
            },
            "item2": {
                "parentDataGuid": "group1",
                "externalId": "SANITAETER1",
                "additionalInfos": {"ressource_name": "Max"},
                "begin": "2026-01-01T07:00:00",
                "end": "2026-01-01T19:00:00"
            },
            "item3": {
                "parentDataGuid": "group2", # Incomplete group (only crew, no vehicle)
                "externalId": "SANITAETER1",
                "additionalInfos": {"ressource_name": "Julia"},
                "begin": "2026-01-01T07:00:00",
                "end": "2026-01-01T19:00:00"
            }
        }
    }
    
    # Logic requires 'begin' and 'end' to be set on the group.
    # The 'KFZ' item sets these for the group. 
    # 'group2' has no 'KFZ' item, so it might lack start/end unless the SANITAETER item sets it?
    # Checking logic: 
    # if eid == "KFZ": ... sets begin/end
    # elif eid ... and rn: ... if not entry["begin"]: entry["begin"] = b
    # So group2 WILL have begin/end from the Sanitaeter item.
    
    results = parse_daily_plan_raw(data)
    assert len(results) == 2
    
    g1 = next(r for r in results if r['vehicle'] == "RTW 1")
    assert g1['crew']['SANITAETER1'] == "Max"
    
    g2 = next(r for r in results if r['vehicle'] == "")
    assert g2['crew']['SANITAETER1'] == "Julia"
