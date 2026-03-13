# backend/brain/intent_classifier.py
import json
from openai import AsyncOpenAI

from backend.config.settings import settings
from backend.utils.logger import logger


class IntentClassifier:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )

    async def classify(self, message: str, context: dict | None = None) -> dict:
        context = context or {}

        prompt = f"""
Classify this user message: "{message}"

Possible intents (pick ONE):
- conversation: casual chat, greetings, general questions
- summarize_emails: check email, find emails, read inbox, "any news from X?", "what's in my mail"
- weather: weather, temperature, forecast, "is it raining", "what's the weather"
- order_food: food, restaurant, order, pizza, delivery
- calendar_event: scheduling, meetings, add event, check calendar
- other: anything else

Return ONLY valid JSON:
{{
  "intent": "one_of_the_above",
  "confidence": 0.0,
  "reason": "one short sentence why"
}}
"""
        try:
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=150,
                response_format={"type": "json_object"},
            )

            content = resp.choices[0].message.content.strip()
            data = json.loads(content)

            allowed_intents = {
                "conversation",
                "summarize_emails",
                "weather",
                "order_food",
                "calendar_event",
                "other",
            }

            intent = data.get("intent", "conversation")
            confidence = data.get("confidence", 0.5)
            reason = data.get("reason", "No reason provided")

            if intent not in allowed_intents:
                logger.warning(f"Unknown classified intent: {intent}")
                intent = "conversation"

            try:
                confidence = float(confidence)
            except Exception:
                confidence = 0.5

            confidence = max(0.0, min(1.0, confidence))

            return {
                "intent": intent,
                "confidence": confidence,
                "reason": reason,
            }

        except Exception as e:
            logger.error(f"Intent classification failed: {e}", exc_info=True)
            return {
                "intent": "conversation",
                "confidence": 0.5,
                "reason": "fallback due to error",
            }