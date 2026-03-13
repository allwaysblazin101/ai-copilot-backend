import json
import logging
from datetime import datetime  # ADD THIS LINE
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
        # Logic: We inject current time so the AI knows what 'tomorrow' means
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        prompt = f"""
        Analyze the user's request: "{user_input}"
        Current Time: {current_time_str}
        
        Decide which tool is required to fulfill this request.

        AVAILABLE ACTIONS:
        - calendar_list: 
          *Use for*: Checking the schedule, seeing upcoming meetings, or "What am I doing today?".
          *Args*: {{"max_results": 5}}

        - create_calendar_event: 
          *Use for*: Adding, scheduling, or booking new events/reminders.
          *Args*: {{"summary": "title", "start_time": "ISO string", "end_time": "ISO string", "location": "optional"}}
          *Note*: If user doesn't specify end_time, default to 1 hour after start_time.

        - summarize_emails: 
          *Use for*: Checking, finding, or reading emails.
          *Args*: {{"query": "Technical Gmail search operator", "count": 3}}
          *Critical*: Convert to Gmail syntax (e.g., "from:Name", "is:unread").
        
        - web_search: 
          *Use for*: Real-time news, weather, or general knowledge.
          *Args*: {{"query": "search terms"}}
        
        - send_sms: 
          *Use for*: Explicit requests to text someone.
        
        - none: 
          *Use for*: General chat or greetings.

        Return ONLY valid JSON:
        {{
          "action": "calendar_list | create_calendar_event | summarize_emails | web_search | send_sms | none",
          "payload": {{}},
          "reasoning": "short explanation"
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a logical routing engine. Output raw JSON only."},
                    {"role": "user", "content": prompt}
                ],
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
