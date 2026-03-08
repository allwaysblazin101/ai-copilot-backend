class BehaviorLearner:

    def __init__(self):
        self.preferences = {}

    def learn(self, key, value):

        if key not in self.preferences:
            self.preferences[key] = []

        self.preferences[key].append(value)

    def predict(self, key):

        if key not in self.preferences:
            return None

        return max(
            set(self.preferences[key]),
            key=self.preferences[key].count
        )
