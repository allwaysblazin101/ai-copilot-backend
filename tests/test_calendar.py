import pytest

from backend.services.google.google_auth import GoogleAuth
from backend.services.calendar.calendar_service import CalendarService


def test_calendar_service_init():
    auth = GoogleAuth()
    calendar = CalendarService(creds=auth.credentials)

    assert calendar is not None
    assert hasattr(calendar, "list_upcoming_events")


def test_list_upcoming_events_returns_list():
    auth = GoogleAuth()
    calendar = CalendarService(creds=auth.credentials)

    result = calendar.list_upcoming_events(max_results=3)

    assert isinstance(result, list)