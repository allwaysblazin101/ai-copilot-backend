# backend/services/calendar/calendar_service.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
from dateutil import parser  # for flexible date parsing

from backend.utils.logger import logger
from backend.config.settings import settings


class CalendarService:
    def __init__(self, creds: Credentials = None):
        self.service = None

        if creds:
            self.service = build("calendar", "v3", credentials=creds)
            logger.success("Google Calendar API initialized")
        else:
            logger.warning("No credentials provided — Calendar disabled")

    def list_upcoming_events(self, max_results: int = 10, time_min: str | None = None):
        """
        List upcoming events from primary calendar.
        time_min: ISO string (UTC), defaults to now.
        """
        if not self.service:
            logger.warning("Calendar service not initialized")
            return []

        try:
            now = time_min or datetime.now(timezone.utc).isoformat()
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            logger.info(f"Found {len(events)} upcoming calendar events")

            formatted = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                formatted.append({
                    "summary": event.get('summary', 'No title'),
                    "start": start,
                    "end": end,
                    "description": event.get('description', ''),
                    "location": event.get('location', ''),
                    "id": event['id']
                })

            return formatted

        except Exception as e:
            logger.error(
                f"Failed to list calendar events: {type(e).__name__} - {str(e)}",
                exc_info=True
            )
            return []

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        timezone: str = "America/Toronto"
    ):
        """Create a new event in primary calendar."""
        if not self.service:
            logger.warning("Calendar service not available — cannot create event")
            return {"error": "Calendar not initialized"}

        try:
            # Parse flexible input times
            start_dt = parser.parse(start_time).isoformat()
            end_dt = parser.parse(end_time).isoformat()

            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {'dateTime': start_dt, 'timeZone': timezone},
                'end': {'dateTime': end_dt, 'timeZone': timezone},
            }

            created = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            logger.success(f"Created calendar event: {summary} (ID: {created.get('id')})")
            return {
                "success": True,
                "event_id": created.get('id'),
                "link": created.get('htmlLink')
            }

        except Exception as e:
            logger.error(f"Failed to create calendar event: {type(e).__name__} - {str(e)}", exc_info=True)
            return {"error": str(e)}