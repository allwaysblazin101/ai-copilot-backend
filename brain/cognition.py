import random


class CognitionBrain:

    async def think(self, message: str):

        emotional_weight = random.uniform(0.5, 1.0)
        reasoning_weight = random.uniform(0.5, 1.0)

        score = (emotional_weight + reasoning_weight) / 2

        if score > 0.75:
            return "provide helpful supportive response"

        return "ask user for clarification"