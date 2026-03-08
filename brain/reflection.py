# backend/brain/reflection.py
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class ReflectionModule:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def analyze(
        self,
        execution_results: List[Dict],
        intent: str,
        original_query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Post-execution reflection: Assess if the tools solved the query.
        Returns whether complete + specific feedback for planner.
        """
        if not execution_results:
            return {"complete": True, "feedback": "No tools executed — direct reasoning sufficient."}

        # Build rich context for judgment
        results_summary = self._summarize_results(execution_results)
        prefs = json.dumps(context.get("persistent", {}), indent=2)
        calendar = self._summarize_calendar(context.get("calendar", []))

        prompt = f"""
You are a strict quality control auditor for an AI assistant.

Original user query: "{original_query}"
Intent: {intent}
User preferences/facts: {prefs}
Calendar: {calendar or 'None'}

Execution results:
{results_summary}

Evaluate:
1. Did tools return meaningful, error-free data?
2. Is there enough information to fully answer the query?
3. If order_food → did it return real options (not just quotes)?
4. If web_search → did it provide relevant, up-to-date facts?
5. If incomplete: What specific next step or info is missing?

Respond ONLY with JSON:
{{
  "complete": true/false,
  "feedback": "Short, actionable instruction for planner (e.g. 'Need better restaurant options' or 'Search again with different query')",
  "suggested_adjustment": "optional new tool or step if needed"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Low variance for reliable judgment
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content.strip())
            return result

        except Exception as e:
            logger.error(f"Reflection failed: {e}", exc_info=True)
            return {"complete": True, "feedback": "Reflection error — proceeding to synthesis."}

    async def extract_knowledge(
        self,
        query: str,
        output: str,
        tool_results: List[Dict],
        user_id: str = "default"
    ) -> List[Dict[str, str]]:
        """
        Extract new facts/preferences from interaction for long-term memory.
        Returns list of {"key": "...", "value": "...", "confidence": 0.0-1.0}
        """
        results_summary = self._summarize_results(tool_results)

        prompt = f"""
From this interaction, extract any new, memorable facts about the user.

Query: "{query}"
AI response: "{output}"
Tool results: {results_summary}

Examples of facts to extract:
- Name changes ("call me Alex" → name: Alex)
- Preferences ("I love spicy food" → favorite_food: spicy food)
- Allergies, dislikes, locations, routines

Only include facts with high confidence.
Output JSON:
{{
  "facts": [
    {{"key": "favorite_food", "value": "spicy food", "confidence": 0.9}},
    ...
  ]
}}
If nothing memorable, return empty array.
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content.strip())
            return data.get("facts", [])

        except Exception as e:
            logger.error(f"Knowledge extraction failed: {e}")
            return []

    def _summarize_results(self, results: List[Dict]) -> str:
        if not results:
            return "No tool results."
        summaries = []
        for r in results:
            tool = r.get("tool", "unknown")
            res = r.get("result", {})
            if isinstance(res, dict):
                if "answer" in res:
                    summaries.append(f"{tool}: {res['answer'][:200]}")
                elif "results" in res:
                    summaries.append(f"{tool}: {len(res['results'])} results found")
                else:
                    summaries.append(f"{tool}: {json.dumps(res)[:200]}")
            else:
                summaries.append(f"{tool}: {str(res)[:200]}")
        return "\n".join(summaries)

    def _summarize_calendar(self, events: List[Dict]) -> str:
        if not events:
            return "No upcoming events."
        return "\n".join([f"- {e.get('summary')} at {e.get('start')}" for e in events[:3]])