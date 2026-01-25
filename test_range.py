import asyncio
import sys
from datetime import datetime, timedelta
from src.config import load_credentials
from src.api_async import AsyncIncodeRequests

async def test_range_fetch():
    creds = load_credentials()
    users = creds.get('users', [])
    if not users:
        print("No users found")
        return

    # Use first user (Manuel)
    u = users[0]
    username = u['username']
    print(f"Testing for user: {username}")
    
    async with AsyncIncodeRequests(u.get('base_url', "https://dienstplan.k.roteskreuz.at"), u.get('extra_guids'), username) as client:
        if not await client.login(username, u['password']):
            print("Login failed")
            return

        now = datetime.now()
        start = now
        end = now + timedelta(days=5) # Try 5 days
        
        print(f"Attempting to fetch plan from {start.date()} to {end.date()} (Single Request)...")
        
        # Directly calling the internal fetch which uses loadPlan.json with the range
        results = await client._fetch_daily_plan_items(start, end)
        
        print(f"Result count: {len(results)}")
        if len(results) > 0:
            print("SUCCESS! API returned items for the range.")
            # Check if we have different dates
            dates = set()
            for item in results:
                if item.get('begin'):
                    if isinstance(item['begin'], str):
                         d = datetime.strptime(item['begin'], '%Y-%m-%dT%H:%M:%S').date()
                    else:
                        d = item['begin'].date()
                    dates.add(d)
            print(f"Create coverage: {sorted(list(dates))}")
            if len(dates) > 1:
                print("CONFIRMED: Multi-day fetch works!")
            else:
                print("WARNING: Only returned data for one day despite range request?")
        else:
            print("No data returned (or empty plan).")

if __name__ == "__main__":
    asyncio.run(test_range_fetch())
