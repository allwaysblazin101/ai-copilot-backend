import asyncio
from twilio.rest import Client
from ddgs import DDGS

from backend.security.tool_guard import ToolGuard
from backend.utils.logger import logger
from backend.config.settings import settings
from backend.tools.weather_tool import WeatherTool

# Services
from backend.services.email.email_service import EmailService
from backend.services.shopping.shopping_agent import ShoppingAgent
from backend.services.food.food_order_agent import FoodOrderAgent


class ToolRouter:

    def __init__(self):

        self.twilio_client = None
        self.guard = ToolGuard()
        self.weather_tool = WeatherTool()   # FIX: initialize weather tool

        # Twilio init
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

    # --------------------------------------------------
    # MAIN ENTRY
    # --------------------------------------------------

    async def execute(self, action: str, payload=None):

        payload = payload or {}

        logger.info(f"ToolRouter received action={action} payload={payload}")

        if not self.guard.allow(action):
            return {"error": "Tool blocked by safety policy"}

        handlers = {
            "weather": self.weather,
            "web_search": self.web_search,
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
    # WEATHER
    # --------------------------------------------------

    async def weather(self, payload):

        location = payload.get("location", "Toronto")

        return await self.weather_tool.get_weather(location)

    # --------------------------------------------------
    # WEB SEARCH
    # --------------------------------------------------

    async def web_search(self, payload):

        query = payload.get("query")

        if not query:
            return {"error": "Missing query"}

        def run():

            with DDGS() as ddgs:

                results = list(ddgs.text(query, max_results=5))

                formatted = []

                for r in results:
                    formatted.append({
                        "title": r.get("title"),
                        "snippet": r.get("body"),
                        "url": r.get("href")
                    })

                return formatted

        return await asyncio.to_thread(run)

    # --------------------------------------------------
    # RESTAURANT DISCOVERY
    # --------------------------------------------------

    async def restaurant_search(self, payload):

        cuisine = payload.get("cuisine")
        location = payload.get("location")

        if not cuisine:
            return {"error": "Cuisine required"}

        query = f"best {cuisine} restaurants in {location or 'near me'}"

        def run():

            with DDGS() as ddgs:

                results = list(ddgs.text(query, max_results=6))

                restaurants = []

                for r in results:

                    restaurants.append({
                        "name": r.get("title"),
                        "description": r.get("body"),
                        "url": r.get("href")
                    })

                return restaurants

        return await asyncio.to_thread(run)

    # --------------------------------------------------
    # FOOD ORDERING
    # --------------------------------------------------

    async def order_food(self, payload):

        agent = FoodOrderAgent()

        return await agent.place_order(payload)

    # --------------------------------------------------
    # FOOD SUGGESTIONS
    # --------------------------------------------------

    async def food_suggest(self, payload):

        cuisine = payload.get("cuisine")

        agent = FoodOrderAgent()

        return await agent.suggest(cuisine)

    # --------------------------------------------------
    # SHOPPING
    # --------------------------------------------------

    async def shop_search(self, payload):

        agent = ShoppingAgent()

        return await agent.search(payload.get("query"))

    # --------------------------------------------------
    # SMS
    # --------------------------------------------------

    def send_sms(self, payload):

        if not self.twilio_client:
            return {"error": "Twilio client not initialized"}

        try:

            msg = self.twilio_client.messages.create(
                body=payload.get("body", ""),
                from_=settings.twilio_number_primary,
                to=payload.get("to") or settings.owner_number
            )

            return {"success": True, "sid": msg.sid}

        except Exception as e:
            return {"error": str(e)}

    # --------------------------------------------------
    # EMAIL
    # --------------------------------------------------

    async def reply_email(self, payload):

        try:

            service = EmailService()

            result = await asyncio.to_thread(
                service.send_email,
                payload.get("to"),
                payload.get("subject"),
                payload.get("body")
            )

            return {"success": True, "result": result}

        except Exception as e:
            return {"error": str(e)}

    # --------------------------------------------------
    # CHAT FALLBACK
    # --------------------------------------------------

    def chat(self, payload):

        return {
            "action": "chat",
            "message": payload.get("message", "")
        }