# backend/brain/planner.py
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
        priority: float = 1,
        depends_on: Optional[str] = None,
    ):
        self.tool = tool
        self.args = args
        self.description = description
        self.priority = priority
        self.depends_on = depends_on
        self.status = "pending"
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "args": self.args,
            "description": self.description,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "status": self.status,
        }


class Plan:
    def __init__(self, steps: List[PlanStep]):
        self.steps = sorted(steps, key=lambda s: s.priority)

    def get_next_step(self, execution_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Get next pending step that has no unmet dependencies.
        execution_results is a list like:
        [{"tool": "weather", "result": {...}}, ...]
        """
        completed_tools = [
            item.get("tool")
            for item in execution_results
            if isinstance(item, dict) and item.get("tool")
        ]

        for step in self.steps:
            if step.status == "pending":
                if step.depends_on is None or step.depends_on in completed_tools:
                    return step.to_dict()

        return None

    def update_step(self, tool_name: str, result: Any):
        """Mark first matching pending step as completed/failed and store result."""
        for step in self.steps:
            if step.tool == tool_name and step.status == "pending":
                result_text = str(result).lower()
                step.status = "failed" if "error" in result_text else "completed"
                step.result = result
                break

    def adjust(self, feedback: Optional[str]):
        """Dynamic adjustment based on reflection."""
        if not feedback:
            return

        logger.info(f"Plan adjustment: {feedback}")

        feedback_lower = feedback.lower()
        if "more information" in feedback_lower or "search" in feedback_lower:
            new_step = PlanStep(
                tool="web_search",
                args={"query": feedback},
                description="Follow-up search based on reflection",
                priority=0.5,
            )
            self.steps.insert(0, new_step)
            self.steps = sorted(self.steps, key=lambda s: s.priority)

    def to_list(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.steps]


class Planner:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def create_initial_plan(self, intent: str, context: Dict[str, Any]) -> Plan:
        """
        Generate a dynamic multi-step plan using the user's intent and context.
        """
        if intent in {"conversation", "other"}:
            return Plan([
                PlanStep(
                    tool="none",
                    args={},
                    description="Direct conversational response",
                    priority=1,
                )
            ])

        prompt = self._build_planning_prompt(intent, context)

        try:
            sys_msg = (
                "You are a precise task planner. "
                "Break the user's intent into 1 to 5 steps using only these tools when needed: "
                "weather, web_search, summarize_emails, calendar_list, create_calendar_event, "
                "restaurant_search, order_food, food_suggest, shop_search, send_sms, reply_email, chat. "
                "If no tool is needed, use tool='none'. "
                "Return ONLY JSON in this format: "
                "{'steps': [{'tool': '...', 'args': {}, 'description': '...'}]}"
            )

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=600,
            )

            plan_data = json.loads(response.choices[0].message.content)
            steps_data = plan_data.get("steps", [])

            steps: List[PlanStep] = []
            for i, step_data in enumerate(steps_data, start=1):
                steps.append(
                    PlanStep(
                        tool=step_data.get("tool", "none"),
                        args=step_data.get("args", {}),
                        description=step_data.get("description", "Unnamed step"),
                        priority=i,
                        depends_on=step_data.get("depends_on"),
                    )
                )

            if not steps:
                steps = [PlanStep("none", {}, "Direct reasoning response", priority=1)]

            return Plan(steps)

        except Exception as e:
            logger.error(f"LLM planning failed: {e}", exc_info=True)
            return self._get_static_fallback(intent, context)

    def _build_planning_prompt(self, intent: str, context: Dict[str, Any]) -> str:
        """Build planning prompt from the actual context shape used by MasterBrain."""
        prefs = json.dumps(context.get("preferences", {}), indent=2)

        calendar_items = context.get("calendar_events", [])[:3]
        calendar_text = "\n".join(
            f"- {event.get('summary', 'Untitled')} at {event.get('start', 'unknown time')}"
            for event in calendar_items
            if isinstance(event, dict)
        ) or "No upcoming events."

        semantic_mem = context.get("semantic_memory", [])
        semantic_text = json.dumps(semantic_mem[:3], indent=2, default=str)

        time_str = context.get("current_time", "unknown")
        location = context.get("location", "Toronto")
        intent_confidence = context.get("intent_confidence", "unknown")

        return f"""
Intent: {intent}
Intent confidence: {intent_confidence}

User preferences:
{prefs}

Recent semantic memory:
{semantic_text}

Upcoming calendar events:
{calendar_text}

Current time:
{time_str}

Location:
{location}

Generate a short logical plan using only available tools.
If no tool is needed, return one step with tool "none".
"""

    def _get_static_fallback(self, intent: str, context: Dict[str, Any]) -> Plan:
        """Reliable static plan when LLM planning fails."""
        steps: List[PlanStep] = [PlanStep("none", {}, "General reasoning", priority=1)]

        if intent == "summarize_emails":
            steps = [
                PlanStep(
                    "summarize_emails",
                    {"query": "is:unread label:inbox", "count": 3},
                    "Fetch latest unread emails",
                    priority=1,
                )
            ]

        elif intent == "weather":
            steps = [
                PlanStep(
                    "weather",
                    {"location": context.get("location", "Toronto")},
                    "Fetch weather for current location",
                    priority=1,
                )
            ]

        elif intent in {"web_search", "news", "price"}:
            steps = [
                PlanStep(
                    "web_search",
                    {"query": context.get("last_user_query", intent)},
                    "Fetch real-time information",
                    priority=1,
                ),
                PlanStep("none", {}, "Summarize results", priority=2),
            ]

        elif intent == "order_food":
            steps = [
                PlanStep("food_suggest", {}, "Suggest food options", priority=1),
                PlanStep("order_food", {}, "Place food order if appropriate", priority=2),
            ]

        elif intent in {"calendar_event", "schedule"}:
            steps = [
                PlanStep(
                    "create_calendar_event",
                    {},
                    "Create a calendar event from parsed details",
                    priority=1,
                )
            ]

        hour = datetime.now(timezone.utc).hour
        if 6 <= hour <= 10:
            steps.append(PlanStep("none", {}, "Offer morning briefing", priority=3))

        return Plan(steps)