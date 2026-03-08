from twilio.rest import Client
from backend.config.settings import TWILIO_SID, TWILIO_TOKEN, TWILIO_PHONE

client = Client(TWILIO_SID, TWILIO_TOKEN)

def send_sms(to_number: str, message: str):
    return client.messages.create(
        body=message,
        from_=TWILIO_PHONE,
        to=to_number
    )