import os
from twilio.rest import Client


class TwilioService:

    def __init__(self):

        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_number = os.getenv("TWILIO_NUMBER_PRIMARY")
        self.owner_number = os.getenv("OWNER_NUMBER")

        self.client = Client(self.account_sid, self.auth_token)

    def send_sms(self, message):

        if not self.owner_number:
            return

        self.client.messages.create(
            body=message,
            from_=self.twilio_number,
            to=self.owner_number
        )