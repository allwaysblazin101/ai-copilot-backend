
class SafetyGovernor:

    def init(self):

        # High risk actions require confirmation
        self.dangerous_actions = {
            "delete_email",
            "execute_trade",
            "send_bulk_sms",
            "transfer_money"
        }

    def allow(self, action):

        if not action:
            return False

        return action not in self.dangerous_actions

    def requires_confirmation(self, action):

        return action in self.dangerous_actions

