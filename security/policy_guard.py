class PolicyGuard:

    def __init__(self):

        self.blocked_actions = [
            "hack",
            "illegal",
            "steal",
            "exploit"
        ]

    def allow(self, intent):

        for word in self.blocked_actions:
            if word in intent.lower():
                return False

        return True