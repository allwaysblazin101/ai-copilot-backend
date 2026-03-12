import datetime
from collections import Counter

class MemoryStore:
    def __init__(self):
        # Using a list for now; in production, you'd likely use SQLite or Redis
        self._memory = []
        self._interaction_times = []
        self._persistent_facts = {}

    def get_context(self) -> dict:
        """
        Unified method to return short-term history and facts.
        Matches what BrainEngine and ReasoningModule expect.
        """
        return {
            "short_term": self._memory[-10:],
            "persistent": self._persistent_facts,
            "activity_pattern": self.predict_user_activity_pattern(),
            "current_time": datetime.datetime.now().isoformat()
        }

    def learn(self, message: str, response: str):
        """Stores the interaction and the time it happened."""
        timestamp = datetime.datetime.now()
        
        self._memory.append({
            "role": "user",
            "content": message,
            "timestamp": timestamp.isoformat()
        })
        
        self._memory.append({
            "role": "assistant",
            "content": response,
            "timestamp": timestamp.isoformat()
        })

        self._interaction_times.append(timestamp.hour)

    def predict_user_activity_pattern(self) -> str:
        """Analyze the most frequent hour of interaction."""
        if not self._interaction_times:
            return "unknown"

        common_hour = Counter(self._interaction_times).most_common(1)[0][0]
        return f"active around {common_hour}:00"

    def add_fact(self, key: str, value: str):
        """Store a long-term fact about the user."""
        self._persistent_facts[key] = value
