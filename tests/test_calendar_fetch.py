from backend.services.google.google_auth import GoogleAuth
from backend.services.calendar.calendar_service import CalendarService
from backend.utils.logger import logger
from datetime import datetime, timedelta, timezone

auth = GoogleAuth()
creds = auth.credentials
cal = CalendarService(creds)

if cal.service:
    print("Calendar ready — creating test event...")
    
    # Create a test event 1 hour from now
    start = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    
    result = cal.create_event(
        summary="AI Copilot Test Event",
        start_time=start,
        end_time=end,
        description="This is a test created by the copilot integration",
        location="Virtual"
    )
    print("Create result:", result)

    # Now list events to verify
    events = cal.list_upcoming_events(max_results=5)
    print("Upcoming events after create:")
    for e in events:
        print(f"- {e['start']} | {e['summary']}")
else:
    print("Calendar failed to initialize")