import pytest

from backend.brain.master_brain import MasterBrain
from backend.services.goals.goal_service import GoalService


@pytest.mark.asyncio
async def test_master_brain_goal_capture():
    brain = MasterBrain()
    user_id = "goal_capture_test_user"

    result = await brain.process_query("I want to exercise 3 times a week", user_id=user_id)

    assert isinstance(result, dict)
    assert "answer" in result
    assert result["metadata"]["intent"] == "goal_capture"
    assert result["metadata"]["goal_domain"] == "health"

    goals = await GoalService().list_goals(user_id, domain="health")
    assert any("exercise" in g["title"].lower() for g in goals)
