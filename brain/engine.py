from backend.brain.reasoning import ReasoningModule
from backend.brain.decision_core import DecisionCore
from backend.tools.tool_router import ToolRouter
from backend.memory.memory_store import MemoryStore
from backend.memory.semantic_memory import SemanticMemory

class BrainEngine:

    def __init__(self):
        self.reasoner = ReasoningModule()
        self.decision = DecisionCore()
        self.tools = ToolRouter()
        self.memory = MemoryStore()
        self.semantic = SemanticMemory()

    async def think(self, message):

        # 1. Understand intent
        intent = message.lower()

        # 2. Reason
        response = await self.reasoner.reason(message, None)

        # 3. Decide action
        decision = await self.decision.decide(intent, {})

        # 4. Execute tools if needed
        tool_result = None

        if "action" in decision:
            tool_result = self.tools.execute(decision["action"])

        # 5. Learn
        self.memory.learn(message, response)
        self.semantic.store(message)

        return {
            "response": response,
            "decision": decision,
            "tools": tool_result
        }
