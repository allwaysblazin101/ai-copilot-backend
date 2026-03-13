# backend/services/replies/reply_service.py
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from backend.config.settings import settings
from backend.memory.persistent_memory import PersistentMemoryStore
from backend.utils.logger import logger


class ReplyService:
    def __init__(self):
        self.memory = PersistentMemoryStore()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        ) if settings.openai_api_key else None

    async def draft_sms_reply(self, incoming_text: str, sender: str) -> str:
        fallback = "Thanks for the message — I’ll get back to you soon."

        if not self.client:
            return fallback

        prompt = f"""
You are drafting a short SMS reply on behalf of the user.

Incoming message from: {sender}
Message: {incoming_text}

Rules:
- Keep it under 140 characters
- Be natural and polite
- Do not use emojis
- Do not add explanation
- Return only the reply text
"""

        try:
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=80,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text[:140] if text else fallback
        except Exception as e:
            logger.error(f"Failed to draft SMS reply: {e}", exc_info=True)
            return fallback

    async def save_pending_reply(
        self,
        owner_number: str,
        original_sender: str,
        original_message: str,
        suggested_reply: str,
    ) -> bool:
        payload = {
            "active": True,
            "owner_number": owner_number,
            "original_sender": original_sender,
            "original_message": original_message,
            "suggested_reply": suggested_reply,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self.memory.save_entity(
            f"pending_sms_reply:{owner_number}",
            payload,
        )

    async def get_pending_reply(self, owner_number: str) -> Optional[Dict[str, Any]]:
        data = await self.memory.get_entity(f"pending_sms_reply:{owner_number}")
        if not isinstance(data, dict):
            return None
        if not data.get("active"):
            return None
        return data

    async def clear_pending_reply(self, owner_number: str) -> bool:
        payload = {
            "active": False,
            "cleared_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self.memory.save_entity(
            f"pending_sms_reply:{owner_number}",
            payload,
        )

    async def save_pending_trade(
        self,
        owner_number: str,
        symbol: str,
        action: str,
        quantity: int,
    ) -> bool:
        payload = {
            "active": True,
            "owner_number": owner_number,
            "symbol": symbol.upper(),
            "action": action.upper(),
            "quantity": int(quantity),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self.memory.save_entity(
            f"pending_trade:{owner_number}",
            payload,
        )

    async def get_pending_trade(self, owner_number: str) -> Optional[Dict[str, Any]]:
        data = await self.memory.get_entity(f"pending_trade:{owner_number}")
        if not isinstance(data, dict):
            return None
        if not data.get("active"):
            return None
        return data

    async def clear_pending_trade(self, owner_number: str) -> bool:
        payload = {
            "active": False,
            "cleared_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self.memory.save_entity(
            f"pending_trade:{owner_number}",
            payload,
        )