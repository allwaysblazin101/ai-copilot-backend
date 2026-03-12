# backend/brain/planner.py
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class PlanStep:
    def __init__(
        self,
        tool: str,
        args: Dict[str, Any],
        description: str,
        priority: int = 1,
        depends_on: Optional[str] = None
    ):
        self.tool = tool
        self.args = args
        self.description = description
        self.priority = priority
        self.depends_on = depends_on
        self.status = "pending"  # pending, completed, failed
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "args": self.args,
            "description": self.description,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "status": self.status
        }


class Plan:
    def __init__(self, steps: List[PlanStep]):
        self.steps = sorted(steps, key=lambda s: s.priority)
        self.current_index = 0

    def get_next_step(self, completed_tools: List[str]) -> Optional[Dict]:
        """Get next pending step that has no unmet dependencies."""
        for step in self.steps:
            if step.status == "pending":
                if step.depends_on is None or step.depends_on in completed_tools:
                    return step.to_dict()
        return None

    def update_step(self, tool_name: str, result: Any):
        """Mark step as completed/failed and store result."""
        for step in self.steps:
            if step.tool == tool_name and step.status == "pending":
                step.status = "failed" if isinstance(result, Exception) or "error" in str(result).lower() else "completed"
                step.result = result
                break

    def adjust(self, feedback: str):
        """Dynamic adjustment based on reflection."""
        logger.info(f"Plan adjustment: {feedback}")
        if "more information" in feedback.lower() or "search" in feedback.lower():
            new_step = PlanStep(
                tool="web_search",
                args={"query": feedback},
                description="Follow-up search based on reflection",
                priority=0.5  # insert early
            )
            self.steps.insert(0, new_step)

    def to_list(self) -> List[Dict]:
        return [s.to_dict() for s in self.steps]


class Planner:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def create_initial_plan(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> Plan:
        """
        Generate a dynamic, multi-step plan using LLM based on intent and full context.
        """
        if intent == "conversation" and not context.get("calendar"):
            return Plan([PlanStep(tool="none", args={}, description="Direct conversational response", priority=1)])

        prompt = self._build_planning_prompt(intent, context)

        try:
            # Defined outside the call to avoid syntax/bracket errors
            sys_msg = (
                "You are a precise task planner. Break intent into 2-5 steps. "
                "TOOLS: summarize_emails (args: query, count), calendar_list, web_search, order_food, send_sms. "
                "Output JSON: {'steps': [{'tool': '...', 'args': {}, 'description': '...'}]}"
            )

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=600
            )

            plan_data = json.loads(response.choices[0].message.content)
            steps_data = plan_data.get("steps", [])

            steps = []
            for i, s in enumerate(steps_data, 1):
                steps.append(PlanStep(
                    tool=s.get("tool", "none"),
                    args=s.get("args", {}),
                    description=s.get("description", "Unnamed step"),
                    priority=i
                ))

            if not steps:
                steps.append(PlanStep("none", {}, "Direct reasoning"))

            return Plan(steps)

        except Exception as e:
            logger.error(f"LLM planning failed: {e}", exc_info=True)
            return self._get_static_fallback(intent, context)

    def _build_planning_prompt(self, intent: str, context: Dict) -> str:
        """Rich, structured prompt using all available context."""
        prefs = json.dumps(context.get("persistent", {}), indent=2)
        calendar = "\n".join([f"- {e.get('summary')} at {e.get('start')}" for e in context.get("calendar", [])[:3]]) or "No upcoming events."
        time_str = context.get("current_time", "unknown")
        location = context.get("location", "Toronto")

        return f"""
Intent: {intent}
User query context: Use the following information to plan steps.

User preferences/facts:
{prefs}

Calendar:
{calendar}

Time: {time_str}
Location: {location}

Generate a short, logical plan using only available tools.
"""

    def _get_static_fallback(self, intent: str, context: Dict) -> Plan:
        """Reliable static plan when LLM fails."""
        steps = [PlanStep("none", {}, "General reasoning", priority=1)]

        if intent in ["email", "check_email", "summarize_emails"]:
            steps = [
                PlanStep("summarize_emails", {"query": "is:unread", "count": 3}, "Fetch latest unread emails", priority=1)
            ]

        elif intent in ["web_search", "weather", "news", "price"]:
            steps = [
                PlanStep("web_search", {"query": intent}, "Fetch real-time information", priority=1),
                PlanStep("none", {}, "Summarize results", priority=2)
            ]

        elif intent == "order_food":
            steps = [
                PlanStep("order_food", {}, "Find and present food options", priority=1),
                PlanStep("none", {}, "Confirm with user", priority=2)
            ]

        elif intent in ["calendar_event", "schedule"]:
            steps = [
                PlanStep("create_calendar_event", {}, "Parse and create event", priority=1)
            ]

        # Add proactive morning/evening briefing logic
        hour = datetime.now(timezone.utc).hour
        if 6 <= hour <= 10:
            steps.append(PlanStep("none", {}, "Offer morning briefing", priority=3))

        return Plan(steps)
