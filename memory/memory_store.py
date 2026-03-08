import datetime


class MemoryStore:

    def __init__(self):
        self._memory = []
        self._interaction_times = []

    def retrieve_context(self):
        return self._memory[-10:]

    def learn(self, message, response):

        self._memory.append({
            "input": message,
            "output": response,
            "timestamp": datetime.datetime.now()
        })

        self._interaction_times.append(
            datetime.datetime.now().hour
        )

    def predict_user_activity_pattern(self):

        if not self._interaction_times:
            return "unknown"

        from collections import Counter

        common_hour = Counter(
            self._interaction_times
        ).most_common(1)[0][0]

        return f"User usually interacts around {common_hour}:00"