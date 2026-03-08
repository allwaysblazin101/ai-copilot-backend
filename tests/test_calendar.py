# backend/tests/test_calendar.py
from backend.services.calendar.calendar_service import CalendarService
from backend.services.email.email_service import EmailService
import datetime

email_svc = EmailService()
calendar = CalendarService(email_svc.creds)

print("Upcoming events:")
events = calendar.list_upcoming_events(max_results=5)
for e in events:
    print(f"- {e['start']} → {e['summary']}")

# Example create (comment out after testing!)
# result = calendar.create_event(
#     "AI Test Meeting",
#     datetime.datetime.now().isoformat(),
#     (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(),
#     "Testing calendar integration"
# )
# print(result)