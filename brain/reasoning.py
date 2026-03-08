# backend/brain/reasoning.py
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from openai import OpenAI, AsyncOpenAI
from backend.config.settings import settings

logger = logging.getLogger(__name__)

class ReasoningModule:
    def __init__(self):
        # Async client for better performance in FastAPI/async contexts
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def synthesize(
        self,
        query: str,
        tool_data: List[Dict[str, Any]],
        memory: Dict[str, Any],
        emotion: str = "neutral"
    ) -> Any:
        """
        Final synthesis: merges query, tools, memory, emotion into a natural, structured reply.
        """
        # Prepare inputs
        chat_history = self._format_chat_history(memory.get("short_term", []))
        tool_context = self._format_tool_results(tool_data)
        prefs = json.dumps(memory.get("persistent", {}), indent=2)
        calendar_summary = self._summarize_calendar(memory.get("calendar", []))

        system_prompt = self._build_system_prompt(
            emotion=emotion,
            prefs=prefs,
            location=memory.get("location", "Toronto, Ontario, CA"),
            current_time=memory.get("current_time", datetime.now(timezone.utc).isoformat()),
            calendar=calendar_summary,
            tool_results=tool_context
        )

        messages = [
            {"role": "system", "content": system_prompt},
            *chat_history,
            {"role": "user", "content": query.strip()}
        ]

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # or "gpt-4o-mini" for faster/cheaper
                messages=messages,
                temperature=0.65,  # tighter for consistency
                max_tokens=1000,
                top_p=0.92,
                response_format={"type": "json_object"}
            )

            parsed = json.loads(response.choices[0].message.content.strip())

            class FinalOutput:
                def __init__(self, data: Dict):
                    self.text = data.get("answer", "No response generated.")
                    self.suggestions = data.get("suggestions", [])

            return FinalOutput(parsed)

        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON — falling back to raw text")
            raw = response.choices[0].message.content.strip()
            return type('FallbackOutput', (), {'text': raw, 'suggestions': []})

        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            return type('ErrorOutput', (), {
                'text': "I'm having trouble putting it all together right now — let's try again?",
                'suggestions': []
            })

    def _build_system_prompt(
        self,
        emotion: str,
        prefs: str,
        location: str,
        current_time: str,
        calendar: str,
        tool_results: str
    ) -> str:
        return f"""
You are Calverton's personal AI assistant — warm, concise, capable, and always helpful.

CURRENT CONTEXT:
- Your emotional state / tone: {emotion}
- User's location: {location}
- Current time: {current_time}
- Calendar highlights: {calendar or 'No upcoming events.'}
- Known preferences & facts:
{prefs if prefs.strip() != '{}' else 'None recorded yet — learn from conversation.'}

RECENT CONVERSATION HISTORY (maintain continuity — reference naturally):
{{history_placeholder}}

TOOL RESULTS & REAL-TIME DATA (CRITICAL — prioritize these over internal knowledge):
{tool_results if tool_results else 'No external tools used for this query.'}

CORE RULES:
1. If the query is about the user (name, favorites, preferences), ALWAYS check provided facts/history first.
2. Use conversation history for continuity — never pretend you forgot something said earlier.
3. Be concise for SMS (under 400 chars when possible), warm, and personalize with name/facts.
4. Never say "I searched" or "according to tools" — just state facts confidently.
5. Generate 2–4 short, proactive, context-aware suggestions for what the user might want next.
6. Tone: friendly, professional, confident — use name occasionally when it feels natural.

RESPONSE FORMAT (JSON ONLY — no other text):
{{
  "answer": "Your natural, human-like response here",
  "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]
}}
"""

    def _format_tool_results(self, tool_data: List[Dict]) -> str:
        if not tool_data:
            return ""
        formatted = []
        for entry in tool_data:
            tool = entry.get("tool", "unknown")
            result = entry.get("result", {})
            if isinstance(result, dict):
                # Handle common tool outputs nicely
                if "answer" in result or "summary" in result:
                    content = result.get("answer") or result.get("summary") or str(result)
                elif "results" in result:
                    content = "\n".join([r.get("content", "")[:200] for r in result["results"][:3]])
                else:
                    content = json.dumps(result, indent=2)[:400]
            else:
                content = str(result)[:400]
            formatted.append(f"[{tool.upper()} OUTPUT]\n{content}")
        return "\n\n".join(formatted) or "No tool data."

    def _format_chat_history(self, history: List[Any]) -> List[Dict[str, str]]:
        messages = []
        for entry in history[-10:]:
            if isinstance(entry, dict) and "role" in entry:
                messages.append({
                    "role": entry["role"],
                    "content": str(entry.get("content", ""))[:500]
                })
            else:
                role = "user" if len(messages) % 2 == 0 else "assistant"
                messages.append({"role": role, "content": str(entry)[:500]})
        return messages

    def _summarize_calendar(self, events: List[Dict]) -> str:
        if not events:
            return "No upcoming events."
        summaries = []
        for e in events[:3]:
            start = e.get("start", "unknown")
            summary = e.get("summary", "Event")
            summaries.append(f"- {summary} at {start}")
        return "\n".join(summaries)