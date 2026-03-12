# backend/brain/intent_classifier.py
from openai import AsyncOpenAI
from backend.config.settings import settings
import json

class IntentClassifier:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def classify(self, message: str, context: dict = None) -> dict:
        prompt = f"""
Classify this user message: "{message}"

Possible intents (pick ONE):
- conversation: casual chat, greetings, questions about self
- summarize_emails: check email, find emails, read inbox, "any news from X?", "what's in my mail"
- weather: weather, temperature, forecast, "is it raining", "what's the weather"
- order_food: food, restaurant, order, pizza, delivery
- calendar_event: schedule, meeting, add event, calendar
- other: anything else

Return ONLY JSON:
{{
  "intent": "one_of_the_above",
  "confidence": 0.0_to_1.0,
  "reason": "one sentence why"
}}
"""
        try:
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            # Parse and ensure the intent matches what the Planner expects
            data = json.loads(resp.choices[0].message.content.strip())
            return data
        except Exception:
            return {"intent": "conversation", "confidence": 0.5, "reason": "fallback due to error"}
