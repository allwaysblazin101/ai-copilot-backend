from backend.config.settings import settings
from openai import OpenAI

class ReplyEngine:
    def __init__(self):
        # Use your central settings
        self.client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )

    async def generate_reply(self, incoming_text, context="sms"):
        # Tell the AI to keep it short if it's a text
        style = "concise SMS reply" if context == "sms" else "professional email"
        
        prompt = f"You are a helpful AI assistant. Write a {style} for: {incoming_text}"

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
