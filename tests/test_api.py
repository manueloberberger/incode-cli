import pytest
import pytest_asyncio
from aioresponses import aioresponses
from datetime import datetime
from src.api_async import AsyncIncodeRequests
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

@pytest_asyncio.fixture
async def api():
    client = AsyncIncodeRequests(base_url=MOCK_BASE_URL)
    await client.ensure_session()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_login_flow(api):
    with aioresponses() as m:
        # Mock Login POST
        m.post(f"{MOCK_BASE_URL}/login.php", 
               body=MOCK_LOGIN_SUCCESS, 
               headers={"Set-Cookie": "PHPSESSID=session123; path=/"})
        
        # Mock Index GET (Token extraction logic)
        m.get(f"{MOCK_BASE_URL}/", body=MOCK_LOGIN_SUCCESS)
        
        # Mock Dispo GET
        m.get(f"{MOCK_BASE_URL}/StaffPortal/dispo.php", body="orgUnitDataGuid: 'GUID-XYZ'")

        # Simulate cookie setting (aioresponses doesn't set cookies in session automatically like requests_mock might,
        # but AsyncIncodeRequests checks self.session.cookie_jar)
        # We need to manually inject the cookie into the session's cookie jar for the check to pass?
        # AsyncIncodeRequests code:
        # async with self.session.post(...) as resp:
        #   cookies = self.session.cookie_jar.filter_cookies(self.base_url)
        #   if 'PHPSESSID' not in cookies: raise ...
        
        # aioresponses mock response headers properly, so calling the endpoint *should* theoretically set the cookie 
        # if aiohttp process it. But aioresponses mocks the *request*, it doesn't simulate full browser cookie logic 
        # unless we are careful. 
        # Actually, aiohttp ClientSession will update cookies from response headers if the mock returns them.
        # Let's verify if aioresponses handles Set-Cookie. It usually does if passed in headers.
        
        # Manually inject cookie since aioresponses/aiohttp interaction might not auto-populate it from mock headers in this env
        from yarl import URL
        api.session.cookie_jar.update_cookies({"PHPSESSID": "session123"}, URL(MOCK_BASE_URL))

        success = await api.login("user", "pass")
        
        assert success is True
        assert api.header_key == "x-incode-token"
        assert api.header_value == "ABC-123"
        assert api.org_unit_data_guid == "GUID-XYZ"

@pytest.mark.asyncio
async def test_load_future_duties(api):
    # Pre-configure logged-in state
    api.header_key = "x-incode-token"
    api.header_value = "ABC-123"
    api.org_unit_data_guid = "GUID-XYZ"
    
    with aioresponses() as m:
        # Mock Duties Endpoint
        m.post(f"{MOCK_BASE_URL}/StaffPortal/duties/data/load.json", payload=MOCK_DUTIES_JSON)
        # Mock Archive (empty)
        m.post(f"{MOCK_BASE_URL}/StaffPortal/archive/data/loadDuties.json", payload={"data": []})
        
        duties = await api.load_future_duties(use_cache=False)
        
        assert len(duties) == 1
        d = duties[0]
        assert isinstance(d, Duty)
        assert d.location == "Test Station"
        assert d.vehicle == "RTW 1"
        # Check Timezone adjustment (Basic check if datetime is parsed)
        assert d.begin.year == 2026

@pytest.mark.asyncio
async def test_search_staff(api):
    api.header_key = "x-incode-token"
    api.header_value = "ABC-123"
    api.org_unit_data_guid = "GUID-XYZ"
    
    mock_staff_response = {
        "data": [
            {"vorname": "Max", "nachname": "Mustermann", "personalnummer": "123"},
            {"vorname": "Julia", "nachname": "Musterfrau", "personalnummer": "456"}
        ]
    }
    
    with aioresponses() as m:
        m.post(f"{MOCK_BASE_URL}/StaffPortal/staff/data/getStaff.json", payload=mock_staff_response)
        
        results = await api.search_staff_contact("Muster")
        assert len(results) == 2
        
        # For the specific search, we mock again directly or rely on the previous mock if it matches.
        # AsyncIncodeRequests fetches all if cache/logic dictates or filtering happens post-fetch?
        # AsyncIncodeRequests.search_staff_contact fetches *all* from getStaff.json then filters in memory?
        # Let's check source: 
        # return parse_staff_contact(j, query) -> which filters by query.
        
        # We need to re-mock if we want to be safe, or just reuse the mock if aioresponses allows multiple calls 
        # (default usually consumes the mock unless repeat=True).
        m.post(f"{MOCK_BASE_URL}/StaffPortal/staff/data/getStaff.json", payload=mock_staff_response)
        
        results_specific = await api.search_staff_contact("Julia")
        assert len(results_specific) == 1
        assert results_specific[0]['vorname'] == "Julia"
