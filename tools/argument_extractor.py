# backend/tools/argument_extractor.py
import json
from openai import AsyncOpenAI  # <--- Change this
from backend.config.settings import settings

class ArgumentExtractor:
    def __init__(self):
        # <--- Change this to AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def extract(self, tool_name: str, user_input: str, context: dict):
        prompt = f"""
        Extract tool arguments from this input: "{user_input}"
        Tool: {tool_name}
        Context: {json.dumps(context.get('persistent', {}))}
        
        Return ONLY valid JSON. 
        Example: {{"date": "2024-10-10", "query": "pizza"}}
        """
        # <--- Add 'await' here
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
