import json
import logging
from openai import AsyncOpenAI
from backend.config.settings import settings
from backend.security.policy_guard import PolicyGuard

logger = logging.getLogger(__name__)

class DecisionCore:
    def __init__(self):
        self.guard = PolicyGuard()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def decide(self, user_input: str, data: dict):
        """
        Smarter decision logic using LLM to map user input to tool actions and queries.
        """
        # 1. Security Check
        if not self.guard.allow(user_input):
            logger.warning(f"Policy violation for input: {user_input}")
            return {"action": "none", "status": "blocked"}

        # 2. Intelligent Mapping via LLM
        prompt = f"""
        Analyze the user's request and decide which tool to use.
        User said: "{user_input}"

        AVAILABLE ACTIONS:
        - summarize_emails: Use for checking, reading, or finding emails. 
          Args: {{"query": "A valid Gmail search query", "count": 3}}
          (Example: "is:unread", "from:Uber", "subject:Invoice")
        - web_search: Use for real-time news, weather, or general info.
          Args: {{"query": "search terms"}}
        - send_sms: Use if the user explicitly wants to text someone.
        - none: Use for casual chat or general questions.

        Return ONLY valid JSON:
        {{
          "action": "summarize_emails | web_search | send_sms | none",
          "payload": {{}},
          "reasoning": "short explanation"
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            decision = json.loads(response.choices[0].message.content)
            logger.info(f"🧠 Decision Core result: {decision['action']} - {decision.get('payload')}")
            return decision

        except Exception as e:
            logger.error(f"Decision Core failure: {e}")
            # Reliable fallback for basic keywords
            if "email" in user_input.lower():
                return {"action": "summarize_emails", "payload": {"query": "is:unread", "count": 3}}
            return {"action": "none"}
