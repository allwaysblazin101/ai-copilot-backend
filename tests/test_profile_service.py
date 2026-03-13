import pytest

from backend.services.profile.profile_service import ProfileService


@pytest.mark.asyncio
async def test_profile_service_roundtrip():
    svc = ProfileService()
    user_id = "test_user_profile"

    profile = await svc.get_profile(user_id)
    assert isinstance(profile, dict)
    assert profile["user_id"] == user_id

    updated = await svc.update_profile(
        user_id,
        {
            "alias": "Cal",
            "goals": {
                "health": ["exercise 3x/week"]
            },
            "preferences": {
                "fitness": {"preferred_time": "evening"}
            },
        },
    )

    assert updated["alias"] == "Cal"
    assert "exercise 3x/week" in updated["goals"]["health"]
    assert updated["preferences"]["fitness"]["preferred_time"] == "evening"
