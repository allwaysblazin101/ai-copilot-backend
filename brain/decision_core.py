from backend.security.policy_guard import PolicyGuard


class DecisionCore:

    def __init__(self):
        self.guard = PolicyGuard()

    async def decide(self, intent: str, data: dict):

        # Security First
        if not self.guard.allow(intent):
            return {
                "status": "blocked",
                "reason": "policy violation"
            }

        intent = intent.lower()

        # Routing only — NO EXECUTION HERE ⭐

        if "email" in intent:
            return {
                "intent": "email_analysis"
            }

        if "sms" in intent:
            return {
                "intent": "communication"
            }

        if "trade" in intent:
            return {
                "intent": "finance_trade"
            }

        if "plan" in intent:
            return {
                "intent": "planning"
            }

        return {
            "intent": "chat"
        }