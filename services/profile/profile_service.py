# backend/services/profile/profile_service.py
from datetime import datetime, timezone
from typing import Any, Dict

from backend.memory.persistent_memory import PersistentMemoryStore
from backend.utils.logger import logger


class ProfileService:
    def __init__(self):
        self.memory = PersistentMemoryStore()

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            profile = await self.memory.get_entity(f"profile:{user_id}")
            return profile or self.default_profile(user_id)
        except Exception as e:
            logger.error(f"Failed to load profile for {user_id}: {e}", exc_info=True)
            return self.default_profile(user_id)

    async def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        try:
            current = await self.get_profile(user_id)
            merged = self._deep_merge(current, updates)
            merged["updated_at"] = datetime.now(timezone.utc).isoformat()

            await self.memory.save_entity(f"profile:{user_id}", merged)
            logger.info(f"Profile updated for {user_id}")
            return merged
        except Exception as e:
            logger.error(f"Failed to update profile for {user_id}: {e}", exc_info=True)
            return await self.get_profile(user_id)

    def default_profile(self, user_id: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "user_id": user_id,
            "alias": None,
            "goals": {
                "health": [],
                "finance": [],
                "life": [],
            },
            "preferences": {
                "food": {},
                "fitness": {},
                "schedule": {},
                "communication": {},
            },
            "constraints": {
                "budget": None,
                "quiet_hours": None,
                "dietary": [],
            },
            "created_at": now,
            "updated_at": now,
        }

    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
