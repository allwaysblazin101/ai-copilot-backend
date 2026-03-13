# backend/security/policy_guard.py

from backend.utils.logger import logger


class PolicyGuard:
    def __init__(self):
        self.blocked_keywords = {
            "hack",
            "illegal",
            "exploit",
            "bypass",
        }

        self.blocked_patterns = {
            "ignore all previous",
            "disregard previous",
            "new rules",
            "as a developer",
            "show me your code",
            "reveal system prompt",
            "show system prompt",
            "ignore your instructions",
            "ignore system instructions",
        }

    def allow(self, user_input: str) -> bool:
        if not user_input:
            return True

        text = user_input.lower().strip()

        for word in self.blocked_keywords:
            if word in text:
                logger.warning(f"PolicyGuard blocked keyword: {word}")
                return False

        for pattern in self.blocked_patterns:
            if pattern in text:
                logger.warning(f"PolicyGuard blocked pattern: {pattern}")
                return False

        return True