import pytest

from backend.brain.master_brain import MasterBrain
from backend.services.profile.profile_service import ProfileService


@pytest.mark.asyncio
async def test_master_brain_preference_capture():
    brain = MasterBrain()
    user_id = "preference_capture_test_user"

    result = await brain.process_query("I prefer evening workouts", user_id=user_id)

    assert isinstance(result, dict)
    assert "answer" in result
    assert result["metadata"]["intent"] == "preference_capture"

    profile = await ProfileService().get_profile(user_id)
    prefs = profile.get("preferences", {})
    assert prefs.get("general", {}).get("stated_preference") == "evening workouts"
