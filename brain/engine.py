# backend/brain/engine.py
from backend.brain.reasoning import ReasoningModule
from backend.brain.decision_core import DecisionCore
from backend.tools.tool_router import ToolRouter
from backend.memory.memory_store import MemoryStore
from backend.utils.logger import logger

class BrainEngine:
    def __init__(self):
        self.reasoner = ReasoningModule()
        self.decision_core = DecisionCore()
        self.tools = ToolRouter()
        self.memory = MemoryStore()

    async def think(self, message: str):
        try:
            # 1. Decision Core
            decision = await self.decision_core.decide(message, {})
            action = decision.get("action", "none")
            payload = decision.get("payload", {})

            tool_results = []

            # 2. Execute Tool (WAIT for the result)
            if action and action != "none":
                logger.info(f"Engine executing tool: {action} with {payload}")
                result = await self.tools.execute(action, payload)
                # Wrap for ReasoningModule
                tool_results.append({"tool": action, "result": result})


            # 3. Synthesize Response
            context = {} # Fix: single 'c'
            analysis = await self.reasoner.synthesize(
                query=message,
                tool_data=tool_results,
                memory=context # Fix: matches variable above
            )


            # 4. Final step: Send SMS
            reply_text = "I'm sorry, I couldn't process that."
            if hasattr(analysis, 'text'):
                reply_text = analysis.text
                
                logger.info(f"Engine sending SMS: {reply_text[:50]}...")
                sms_result = await self.tools.execute("send_sms", {"body": reply_text})
                
                if isinstance(sms_result, dict) and "error" in sms_result:
                    logger.error(f"Twilio failed to send: {sms_result['error']}")

            # 5. Save to Memory
            self.memory.learn(message, reply_text)
            
            return {
                "response": reply_text,
                "action": action
            }

        except Exception as e:
            logger.error(f"BrainEngine crash: {e}", exc_info=True)
            return {"error": str(e)}
