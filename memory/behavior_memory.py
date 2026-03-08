
import datetime
from collections import Counter


class BehaviorMemory:

    def init(self):
        self.actions = []

    def record_action(self, action_name):

        self.actions.append(
            datetime.datetime.now().strftime("%H")
        )

    def predict_active_hour(self):

        if not self.actions:
            return None

        hour = Counter(self.actions).most_common(1)[0][0]

        return f"User usually active around {hour}:00"

