import asyncio
from twilio.rest import Client

from backend.security.tool_guard import ToolGuard
from backend.utils.logger import logger
from backend.config.settings import settings
from backend.tools.weather_tool import WeatherTool
from backend.tools.web_search import search_the_web 

# Services
from backend.services.email.email_service import EmailService
from backend.services.shopping.shopping_agent import ShoppingAgent
from backend.services.food.food_order_agent import FoodOrderAgent

class ToolRouter:
    def __init__(self):
        self.twilio_client = None
        self.guard = ToolGuard()
        self.weather_tool = WeatherTool()

        if settings.twilio_account_sid and settings.twilio_auth_token:
            try:
                sid = settings.twilio_account_sid.get_secret_value()
                token = settings.twilio_auth_token.get_secret_value()
                self.twilio_client = Client(sid, token)
                logger.success("Twilio initialized")
            except Exception:
                logger.error("Twilio init failed", exc_info=True)
        else:
            logger.warning("Twilio disabled — missing credentials")

    async def execute(self, action: str, payload=None):
        payload = payload or {}
        logger.info(f"ToolRouter received action={action} payload={payload}")

        if not self.guard.allow(action):
            return {"error": "Tool blocked by safety policy"}

        handlers = {
            "weather": self.weather,
            "web_search": self.web_search,
            "summarize_emails": self.summarize_emails,
            "restaurant_search": self.restaurant_search,
            "order_food": self.order_food,
            "food_suggest": self.food_suggest,
            "shop_search": self.shop_search,
            "send_sms": self.send_sms,
            "reply_email": self.reply_email,
            "chat": self.chat
        }

        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action {action}"}

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload)
            return handler(payload)
        except Exception as e:
            logger.error(f"Tool execution failed: {action}", exc_info=True)
            return {"error": str(e)}

    # --------------------------------------------------
    # TOOLS
    # --------------------------------------------------

    async def summarize_emails(self, payload):
        query = payload.get("query", "is:unread label:inbox")
        count = payload.get("count", 3)
        service = EmailService()
        emails_to_process = []

        try:
            results = service.service.users().messages().list(userId="me", q=query, maxResults=count).execute()
            for msg in results.get("messages", []):
                full_msg = service.get_message(msg["id"])
                if full_msg:
                    headers = full_msg.get("payload", {}).get("headers", [])
                    subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                    sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown")
                    emails_to_process.append(f"From: {sender}\nSubj: {subject}\nSnippet: {full_msg.get('snippet', '')}")

            if not emails_to_process:
                return {"summary": "No matching emails found."}

            email_text = "\n---\n".join(emails_to_process)

            from backend.services.email.email_classifier import EmailClassifier
            classifier = EmailClassifier()
            
            response = classifier.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a personal assistant. Summarize these emails briefly and conversationally."},
                    {"role": "user", "content": email_text}
                ],
                temperature=0.3
            )
            return {"summary": response.choices[0].message.content}
        except Exception as e:
            logger.error(f"Summarize tool error: {e}")
            return {"error": str(e)}

    async def weather(self, payload):
        location = payload.get("location", "Toronto")
        return await self.weather_tool.get_weather(location)

    async def web_search(self, payload):
        query = payload.get("query")
        if not query: return {"error": "Missing query"}
        return await search_the_web(query, deep_dive=payload.get("deep_dive", False))

    async def restaurant_search(self, payload):
        cuisine = payload.get("cuisine")
        if not cuisine: return {"error": "Cuisine required"}
        query = f"best {cuisine} restaurants in {payload.get('location', 'near me')}"
        search_results = await search_the_web(query)
        if search_results.get("status") == "success":
            return {"results": search_results.get("sources"), "summary": search_results.get("answer")}
        return search_results

    async def order_food(self, payload):
        return await FoodOrderAgent().place_order(payload)

    async def food_suggest(self, payload):
        return await FoodOrderAgent().suggest(payload.get("cuisine"))

    async def shop_search(self, payload):
        return await ShoppingAgent().search(payload.get("query"))

    def send_sms(self, payload):
        if not self.twilio_client: return {"error": "Twilio disabled"}
        msg = self.twilio_client.messages.create(
            body=payload.get("body", ""),
            from_=settings.twilio_number_primary,
            to=payload.get("to") or settings.owner_number
        )
        return {"success": True, "sid": msg.sid}

    async def reply_email(self, payload):
        service = EmailService()
        result = await asyncio.to_thread(service.send_email, payload.get("to"), payload.get("subject"), payload.get("body"))
        return {"success": True, "result": result}

    def chat(self, payload):
        return {"action": "chat", "message": payload.get("message", "")}
