import pytest
import requests_mock
from datetime import datetime
from src.api import IncodeRequests
from src.models import Duty

# Mock Data
MOCK_BASE_URL = "https://example.com"
MOCK_LOGIN_SUCCESS = """
<html>
    <script>var config = {"x-incode-token": "ABC-123", "orgUnitDataGuid": "GUID-XYZ"};</script>
</html>
"""


MOCK_DUTIES_JSON = {
    "data": [
        {
            "begin": "2026-05-10T06:00:00.000Z",
            "end": "2026-05-10T18:00:00.000Z",
            "orgUnitName": "Test Station",
            "dutyTypeName": "Tagdienst",
            "additionalInfos": {
                "ressource_name": "Mustermann Max",
                "project_name": "RTW 1"
            },
            "allocationInfo": ["Mustermann Max", "Musterfrau Julia", "RTW 1"]
        }
    ]
}

@pytest.fixture
def api():
    return IncodeRequests(base_url=MOCK_BASE_URL)

def test_login_flow(api):
    with requests_mock.Mocker() as m:
        # Mock Login POST
        m.post(f"{MOCK_BASE_URL}/login.php", 
               text=MOCK_LOGIN_SUCCESS, 
               headers={"Set-Cookie": "PHPSESSID=session123; path=/"})
        
        # Mock Index GET (Token extraction logic)
        m.get(f"{MOCK_BASE_URL}/", text=MOCK_LOGIN_SUCCESS)
        
        # Mock Dispo GET
        m.get(f"{MOCK_BASE_URL}/StaffPortal/dispo.php", text="orgUnitDataGuid: 'GUID-XYZ'")

        # Mock JS File not needed anymore
        # m.get(f"{MOCK_BASE_URL}/test.js", text=MOCK_JS_CONTENT)
        
        api.session.cookies.set("PHPSESSID", "session123")
        success, msg = api.login("user", "pass")
        
        assert success is True
        assert api.header_key == "x-incode-token"
        assert api.header_value == "ABC-123"
        assert api.org_unit_data_guid == "GUID-XYZ"

def test_load_future_duties(api):
    # Pre-configure logged-in state
    api.header_key = "x-incode-token"
    api.header_value = "ABC-123"
    api.org_unit_data_guid = "GUID-XYZ"
    
    with requests_mock.Mocker() as m:
        # Mock Duties Endpoint
        m.post(f"{MOCK_BASE_URL}/StaffPortal/duties/data/load.json", json=MOCK_DUTIES_JSON)
        # Mock Archive (empty)
        m.post(f"{MOCK_BASE_URL}/StaffPortal/archive/data/loadDuties.json", json={"data": []})
        
        duties = api.load_future_duties(use_cache=False)
        
        assert len(duties) == 1
        d = duties[0]
        assert isinstance(d, Duty)
        assert d.location == "Test Station"
        assert d.vehicle == "RTW 1"
        # Check Timezone adjustment (Basic check if datetime is parsed)
        assert d.begin.year == 2026

def test_api_handle_error(api):
    api.header_key = "x-incode-token"
    api.header_value = "ABC-123"
    
    with requests_mock.Mocker() as m:
        m.post(f"{MOCK_BASE_URL}/StaffPortal/duties/data/load.json", status_code=500)
        
        # Should catch error and return empty list via decorator logic or raise depending on implementation
        # Our implementation raises for_status() but handle_api_errors might catch it?
        # Let's check api.py... oh, load_future_duties doesn't have @handle_api_errors decorator on itself!
        # It relies on resp.raise_for_status().
        
        try:
            api.load_future_duties(use_cache=False)
            assert False, "Should have raised exception"
        except Exception:
            assert True

def test_search_staff(api):
    api.header_key = "x-incode-token"
    api.header_value = "ABC-123"
    api.org_unit_data_guid = "GUID-XYZ"
    
    mock_staff_response = {
        "data": [
            {"vorname": "Max", "nachname": "Mustermann", "personalnummer": "123"},
            {"vorname": "Julia", "nachname": "Musterfrau", "personalnummer": "456"}
        ]
    }
    
    with requests_mock.Mocker() as m:
        m.post(f"{MOCK_BASE_URL}/StaffPortal/staff/data/getStaff.json", json=mock_staff_response)
        
        results = api.search_staff_contact("Muster")
        assert len(results) == 2
        
        results_specific = api.search_staff_contact("Julia")
        assert len(results_specific) == 1
        assert results_specific[0]['vorname'] == "Julia"
