import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

# Core AI modules
from backend.brain.emotional_model import EmotionalModel
from backend.brain.behavior_predictor import BehaviorPredictor
from backend.brain.reasoning import ReasoningModule
from backend.brain.planner import Planner
from backend.brain.reflection import ReflectionModule
from backend.brain.intent_classifier import IntentClassifier

# Security & Tools
from backend.security.logging_system import AILogger
from backend.security.policy_guard import PolicyGuard
from backend.tools.tool_router import ToolRouter
from backend.tools.argument_extractor import ArgumentExtractor

# Memory
from backend.memory.memory_store import MemoryStore
from backend.memory.persistent_memory import PersistentMemoryStore
from backend.memory.vector_memory import VectorMemory

# Services
from backend.services.google.google_auth import GoogleAuth
from backend.services.calendar.calendar_service import CalendarService
from backend.services.food.food_order_agent import FoodOrderAgent
from backend.services.payment.stripe_service import StripeService
from backend.services.goals.goal_service import GoalService
from backend.services.profile.profile_service import ProfileService

from backend.utils.logger import logger


class MasterBrain:
    def __init__(self):
        self.google_auth = GoogleAuth()

        # Initialize Calendar only if auth is valid
        self.calendar = (
            CalendarService(creds=self.google_auth.credentials)
            if self.google_auth.credentials
            else None
        )

        self.stripe = StripeService()
        self.food_agent = FoodOrderAgent()

        self.reasoner = ReasoningModule()
        self.planner = Planner()
        self.reflector = ReflectionModule()
        self.intent_engine = IntentClassifier()
        self.extractor = ArgumentExtractor()

        self.behavior = BehaviorPredictor()
        self.emotions = EmotionalModel()
        self.short_term = MemoryStore()
        self.persistent = PersistentMemoryStore()
        self.vector = VectorMemory()

        self.goal_service = GoalService()
        self.profile_service = ProfileService()

        # Tool Router Integration
        self.router = ToolRouter()
        self.guard = PolicyGuard()
        self.security_logger = AILogger()

    @staticmethod
    def _extract_text(payload: Any) -> str:
        """Safely extracts text string from a dict, object, or string."""
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            return payload.get("answer", str(payload))
        return getattr(payload, "text", str(payload))

    async def _maybe_await(self, value):
        if asyncio.iscoroutine(value):
            return await value
        return value

    async def process_query(
        self,
        user_input: str,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        try:
            # Step 1: Context Assembly
            context = await self._assemble_context(user_input, user_id)

            # Step 2: Intent Classification
            intent_result = await self.intent_engine.classify(user_input, context)
            intent = intent_result.get("intent", "conversation")
            confidence = intent_result.get("confidence", 0.0)

            context.update(
                {
                    "intent": intent,
                    "intent_confidence": confidence,
                    "last_user_query": user_input,
                    "user_id": user_id,
                }
            )

            # Step 3: Security Guard
            if not self.guard.allow(user_input):
                return {
                    "answer": "I'm sorry, my security policy doesn't allow me to perform that action.",
                    "emotion": "protective",
                }

            # Step 3.5: Goal capture shortcut
            goal_response = await self._maybe_capture_goal(user_input, user_id)
            if goal_response is not None:
                return goal_response

            # Step 4: Planning & Execution Loop
            execution_results = []
            plan = await self.planner.create_initial_plan(intent, context)

            for _ in range(3):
                current_step = plan.get_next_step(execution_results)

                if not current_step or current_step.get("tool") == "none":
                    break

                tool_name = current_step.get("tool")
                args = current_step.get("args", {}) or {}

                if self.extractor and confidence >= 0.6:
                    try:
                        extracted_args = await self.extractor.extract(
                            tool_name,
                            user_input,
                            context,
                        )
                        if extracted_args:
                            args = extracted_args
                    except Exception as e:
                        logger.warning(
                            f"Argument extraction failed for {tool_name}: {e}",
                            exc_info=True,
                        )

                try:
                    tool_result = await asyncio.wait_for(
                        self.router.execute(tool_name, args),
                        timeout=10.0,
                    )
                    execution_results.append({"tool": tool_name, "result": tool_result})
                    plan.update_step(tool_name, tool_result)

                    reflection = await asyncio.wait_for(
                        self.reflector.analyze(
                            execution_results,
                            intent,
                            user_input,
                            context,
                        ),
                        timeout=8.0,
                    )

                    if reflection.get("complete", False):
                        break

                    plan.adjust(reflection.get("feedback"))

                except asyncio.TimeoutError:
                    logger.warning(f"Tool execution timed out: {tool_name}")
                    execution_results.append(
                        {"tool": tool_name, "result": "Error: Tool timed out."}
                    )
                    plan.update_step(tool_name, {"error": "Tool timed out"})
                    break

                except Exception as e:
                    logger.error(
                        f"Tool execution error ({tool_name}): {e}",
                        exc_info=True,
                    )
                    execution_results.append(
                        {"tool": tool_name, "result": f"Error: {str(e)}"}
                    )
                    plan.update_step(tool_name, {"error": str(e)})
                    break

            # Step 5: Final Synthesis
            emotional_state = self.emotions.update(user_input, context)

            if asyncio.iscoroutinefunction(self.reasoner.synthesize):
                final_output = await self.reasoner.synthesize(
                    query=user_input,
                    tool_data=execution_results,
                    memory=context,
                    emotion=emotional_state,
                )
            else:
                final_output = self.reasoner.synthesize(
                    query=user_input,
                    tool_data=execution_results,
                    memory=context,
                    emotion=emotional_state,
                )

            reply_answer = self._extract_text(final_output)

            # Step 6: Background Learning
            task = asyncio.create_task(
                self._learn(user_id, user_input, reply_answer, execution_results)
            )
            task.add_done_callback(self._handle_background_task_result)

            return {
                "answer": reply_answer,
                "emotion": emotional_state,
                "plan": plan.to_list(),
                "proactive_suggestions": self._generate_proactive_suggestions(context),
                "metadata": {
                    "intent": intent,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "location": context.get("location", "Unknown"),
                },
            }

        except Exception as e:
            logger.error(f"Critical Brain Failure: {str(e)}", exc_info=True)
            return {
                "answer": "I'm having trouble thinking clearly right now.",
                "error": True,
            }

    async def _maybe_capture_goal(self, user_input: str, user_id: str) -> Dict[str, Any] | None:
        text = user_input.lower().strip()

        goal_prefixes = [
            "i want to ",
            "i wanna ",
            "my goal is to ",
            "help me ",
        ]

        matched_prefix = next((p for p in goal_prefixes if text.startswith(p)), None)
        if not matched_prefix:
            return None

        goal_text = user_input[len(matched_prefix):].strip()
        if not goal_text:
            return None

        domain = self._infer_goal_domain(goal_text)

        goal = await self.goal_service.add_goal(
            user_id=user_id,
            domain=domain,
            title=goal_text,
        )

        profile = await self.profile_service.get_profile(user_id)
        alias = profile.get("alias") or "there"

        suggestions_map = {
            "health": [
                "Want me to help turn this into a weekly routine?",
                "I can also help with reminders, meals, and workout planning.",
            ],
            "finance": [
                "Want me to help turn this into a finance routine?",
                "I can also help with savings reminders and market check-ins.",
            ],
            "life": [
                "Want me to help turn this into a step-by-step plan?",
                "I can also help with scheduling, reminders, and follow-through.",
            ],
        }

        answer = (
            f"Got it {alias} — I saved this as a {domain} goal: '{goal['title']}'. "
            f"{suggestions_map.get(domain, ['Want me to help break it down into steps?'])[0]}"
        )

        return {
            "answer": answer,
            "emotion": "supportive",
            "plan": [],
            "proactive_suggestions": suggestions_map.get(domain, []),
            "metadata": {
                "intent": "goal_capture",
                "goal_id": goal["id"],
                "goal_domain": domain,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _infer_goal_domain(self, goal_text: str) -> str:
        text = goal_text.lower()

        health_keywords = [
            "exercise", "work out", "workout", "gym", "run", "fitness",
            "diet", "meal", "nutrition", "sleep", "healthy", "lose weight",
            "gain muscle", "meal prep",
        ]
        finance_keywords = [
            "save money", "budget", "invest", "trading", "portfolio", "stocks",
            "finance", "financial", "income", "debt", "spend less",
        ]

        if any(k in text for k in health_keywords):
            return "health"
        if any(k in text for k in finance_keywords):
            return "finance"
        return "life"

    async def _assemble_context(self, text: str, user_id: str) -> Dict[str, Any]:
        """Gather memory, preferences, and external context concurrently."""
        try:
            vector_task = (
                self._maybe_await(self.vector.search(text, limit=3))
                if self.vector
                else asyncio.sleep(0, result=[])
            )

            prefs_task = self._maybe_await(
                self.persistent.get_entity("user_preferences")
            )
            profile_task = self.profile_service.get_profile(user_id)
            calendar_task = self._get_calendar_events()

            results = await asyncio.gather(
                prefs_task,
                vector_task,
                profile_task,
                calendar_task,
                return_exceptions=True,
            )

            prefs = results[0] if not isinstance(results[0], Exception) else {}
            semantic_mem = results[1] if not isinstance(results[1], Exception) else []
            profile = results[2] if not isinstance(results[2], Exception) else {}
            events = results[3] if not isinstance(results[3], Exception) else []

            short_term = await self._maybe_await(
                self.persistent.recall_recent(user_id=user_id, limit=10)
            )

            return {
                "short_term": short_term or [],
                "preferences": prefs or {},
                "profile": profile or {},
                "semantic_memory": semantic_mem or [],
                "calendar_events": events or [],
                "current_time": datetime.now(timezone.utc).isoformat(),
                "last_user_query": text,
                "user_id": user_id,
            }

        except Exception as e:
            logger.error(f"Context assembly failed: {e}", exc_info=True)
            return {
                "short_term": [],
                "preferences": {},
                "profile": {},
                "semantic_memory": [],
                "calendar_events": [],
                "current_time": datetime.now(timezone.utc).isoformat(),
                "last_user_query": text,
                "user_id": user_id,
            }

    async def _get_calendar_events(self) -> List[Any]:
        if not self.calendar:
            return []

        try:
            return await self.calendar.get_upcoming_events(limit=5)
        except Exception as e:
            logger.warning(f"Calendar fetch failed: {e}", exc_info=True)
            return []

    async def _learn(
        self,
        user_id: str,
        query: str,
        answer: str,
        tools: List[Dict[str, Any]],
    ):
        """Save interaction to persistent and vector memory."""
        try:
            await self._maybe_await(
                self.persistent.save(
                    query,
                    answer,
                    context={"user_id": user_id, "tools": tools},
                )
            )

            if self.vector:
                await self._maybe_await(self.vector.add_interaction(query, answer))

        except Exception as e:
            logger.error(f"Learning failure: {e}", exc_info=True)

    def _handle_background_task_result(self, task: asyncio.Task):
        try:
            task.result()
        except Exception as e:
            logger.error(f"Background task failed: {e}", exc_info=True)

    def _generate_proactive_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Generate simple dynamic suggestions based on context."""
        suggestions = ["What's the weather?", "Check my schedule"]

        if context.get("calendar_events"):
            suggestions.insert(0, "What's next on my calendar?")

        profile = context.get("profile", {}) or {}
        goals = profile.get("goals", {}) if isinstance(profile, dict) else {}

        if goals.get("health"):
            suggestions.append("Help me stay on track with my health goals")
        if goals.get("finance"):
            suggestions.append("Check in on my finance goals")

        return suggestions
