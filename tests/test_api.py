import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer
from src.api_async import AsyncIncodeRequests
from src.models import Duty

# Mock Data
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
async def api(monkeypatch):
    """Exercise real HTTP responses without relying on aiohttp internals."""
    async def login(request):
        response = web.Response(text=MOCK_LOGIN_SUCCESS)
        response.set_cookie("PHPSESSID", "session123")
        return response

    async def index(request):
        return web.Response(text=MOCK_LOGIN_SUCCESS)

    async def dispo(request):
        return web.Response(text="orgUnitDataGuid: 'GUID-XYZ'")

    async def duties(request):
        return web.json_response(MOCK_DUTIES_JSON)

    async def archive(request):
        return web.json_response({"data": []})

    async def staff(request):
        return web.json_response({"data": [
            {"vorname": "Max", "nachname": "Mustermann", "personalnummer": "123"},
            {"vorname": "Julia", "nachname": "Musterfrau", "personalnummer": "456"},
        ]})

    app = web.Application()
    app.router.add_post("/login.php", login)
    app.router.add_get("/", index)
    app.router.add_get("/StaffPortal/dispo.php", dispo)
    app.router.add_post("/StaffPortal/duties/data/load.json", duties)
    app.router.add_post("/StaffPortal/archive/data/loadDuties.json", archive)
    app.router.add_post("/StaffPortal/staff/data/getStaff.json", staff)
    # localhost allows normal cookie handling; no manual cookie injection.
    async with TestServer(app, host="localhost") as server:
        client = AsyncIncodeRequests(base_url=str(server.make_url("/")).rstrip("/"))
        monkeypatch.setattr(client, "_get_cached_data", lambda key: None)
        monkeypatch.setattr(client, "_set_cached_data", lambda key, data: None)
        async with client:
            yield client


@pytest.mark.asyncio
async def test_login_flow(api):
    assert await api.login("user", "pass") is True
    assert api.header_key == "x-incode-token"
    assert api.header_value == "ABC-123"
    assert api.org_unit_data_guid == "GUID-XYZ"
    assert any(cookie.key == "PHPSESSID" for cookie in api.session.cookie_jar)


@pytest.mark.asyncio
async def test_load_future_duties(api):
    api.header_key = "x-incode-token"
    api.header_value = "ABC-123"
    api.org_unit_data_guid = "GUID-XYZ"
    duties = await api.load_future_duties(use_cache=False)
    assert len(duties) == 1
    duty = duties[0]
    assert isinstance(duty, Duty)
    assert duty.location == "Test Station"
    assert duty.vehicle == "RTW 1"
    assert duty.begin.year == 2026


@pytest.mark.asyncio
async def test_search_staff(api):
    api.header_key = "x-incode-token"
    api.header_value = "ABC-123"
    api.org_unit_data_guid = "GUID-XYZ"
    assert len(await api.search_staff_contact("Muster")) == 2
    results = await api.search_staff_contact("Julia")
    assert len(results) == 1
    assert results[0]["vorname"] == "Julia"
