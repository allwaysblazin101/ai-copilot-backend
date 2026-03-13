import pytest

from backend.services.goals.goal_service import GoalService


@pytest.mark.asyncio
async def test_goal_service_add_and_update():
    svc = GoalService()
    user_id = "test_goal_user"

    goal = await svc.add_goal(
        user_id=user_id,
        domain="health",
        title="Exercise 3x per week",
        target={"frequency_per_week": 3},
        preferences={"preferred_time": "evening"},
    )

    assert goal["domain"] == "health"
    assert goal["title"] == "Exercise 3x per week"
    assert goal["status"] == "active"
    assert goal["target"]["frequency_per_week"] == 3

    goals = await svc.list_goals(user_id, domain="health")
    assert any(g["id"] == goal["id"] for g in goals)

    updated = await svc.pause_goal(user_id, goal["id"])
    assert updated is not None
    assert updated["status"] == "paused"

    completed = await svc.complete_goal(user_id, goal["id"])
    assert completed is not None
    assert completed["status"] == "completed"
