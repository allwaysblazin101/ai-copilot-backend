
class EmailCognition:

    def analyze(self, email_text):

        if "invoice" in email_text.lower():
            return "finance"

        if "meeting" in email_text.lower():
            return "calendar"

        if "urgent" in email_text.lower():
            return "high_priority"

        return "general"
