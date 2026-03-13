# backend/services/goals/goal_service.py
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from backend.services.profile.profile_service import ProfileService
from backend.utils.logger import logger


class GoalService:
    VALID_DOMAINS = {"health", "finance", "life"}

    def __init__(self):
        self.profile_service = ProfileService()

    async def list_goals(self, user_id: str, domain: str | None = None) -> List[Dict[str, Any]]:
        profile = await self.profile_service.get_profile(user_id)

        if domain:
            return profile.get("goals", {}).get(domain, [])

        all_goals: List[Dict[str, Any]] = []
        for goals in profile.get("goals", {}).values():
            all_goals.extend(goals)
        return all_goals

    async def add_goal(
        self,
        user_id: str,
        domain: str,
        title: str,
        target: Dict[str, Any] | None = None,
        preferences: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if domain not in self.VALID_DOMAINS:
            raise ValueError(f"Invalid goal domain: {domain}")

        now = datetime.now(timezone.utc).isoformat()
        goal = {
            "id": f"goal_{uuid4().hex[:10]}",
            "domain": domain,
            "title": title,
            "status": "active",
            "target": target or {},
            "preferences": preferences or {},
            "created_at": now,
            "updated_at": now,
        }

        profile = await self.profile_service.get_profile(user_id)
        profile.setdefault("goals", {}).setdefault(domain, []).append(goal)

        await self.profile_service.update_profile(
            user_id,
            {
                "goals": profile["goals"],
            },
        )

        logger.info(f"Added goal for {user_id}: {title}")
        return goal

    async def update_goal(
        self,
        user_id: str,
        goal_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any] | None:
        profile = await self.profile_service.get_profile(user_id)

        for domain, goals in profile.get("goals", {}).items():
            for goal in goals:
                if goal.get("id") == goal_id:
                    goal.update(updates)
                    goal["updated_at"] = datetime.now(timezone.utc).isoformat()

                    await self.profile_service.update_profile(
                        user_id,
                        {
                            "goals": profile["goals"],
                        },
                    )

                    logger.info(f"Updated goal {goal_id} for {user_id}")
                    return goal

        logger.warning(f"Goal {goal_id} not found for {user_id}")
        return None

    async def complete_goal(self, user_id: str, goal_id: str) -> Dict[str, Any] | None:
        return await self.update_goal(
            user_id,
            goal_id,
            {
                "status": "completed",
            },
        )

    async def pause_goal(self, user_id: str, goal_id: str) -> Dict[str, Any] | None:
        return await self.update_goal(
            user_id,
            goal_id,
            {
                "status": "paused",
            },
        )
