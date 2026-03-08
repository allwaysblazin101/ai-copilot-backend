import datetime

class BehaviorPredictor:

    def predict_next_action(self, history):

        hour = datetime.datetime.now().hour

        if 6 <= hour <= 9:
            return "morning_assistant_mode"

        if 9 < hour < 17:
            return "work_support_mode"

        if 18 <= hour:
            return "life_management_mode"

        return "idle_mode"
