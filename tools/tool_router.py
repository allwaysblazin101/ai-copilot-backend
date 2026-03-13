# backend/tools/tool_router.py
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
from backend.services.finance.ibkr_service import IBKRService


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
            logger.warning(f"Tool blocked by safety policy: {action}")
            return {"error": "Tool blocked by safety policy"}

        handlers = {
            "weather": self.weather,
            "web_search": self.web_search,
            "summarize_emails": self.summarize_emails,
            "calendar_list": self.calendar_list,
            "create_calendar_event": self.create_event,
            "restaurant_search": self.restaurant_search,
            "order_food": self.order_food,
            "food_suggest": self.food_suggest,
            "shop_search": self.shop_search,
            "send_sms": self.send_sms,
            "ibkr_portfolio_summary": self.ibkr_portfolio_summary,
            "reply_email": self.reply_email,
            "chat": self.chat,
            "ibkr_cancel_order": self.ibkr_cancel_order,
            "ibkr_account_summary": self.ibkr_account_summary,
            "ibkr_positions": self.ibkr_positions,
            "ibkr_open_orders": self.ibkr_open_orders,
            "ibkr_place_paper_order": self.ibkr_place_paper_order,
        }

        handler = handlers.get(action)
        if not handler:
            logger.warning(f"Unknown action requested: {action}")
            return {"error": f"Unknown action {action}"}

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload)
            return handler(payload)
        except Exception as e:
            logger.error(f"Tool execution failed: {action}", exc_info=True)
            return {"error": str(e)}

    # --------------------------------------------------
    # CALENDAR TOOLS
    # --------------------------------------------------

    async def calendar_list(self, payload):
        """Fetch upcoming events."""
        from backend.services.calendar.calendar_service import CalendarService
        from backend.services.google.google_auth import GoogleAuth

        auth = GoogleAuth()
        service = CalendarService(creds=auth.credentials)

        max_res = payload.get("max_results", 5)
        events = service.list_upcoming_events(max_results=max_res)

        if not events:
            return {"summary": "Your calendar is clear!"}

        return {"results": events}

    async def create_event(self, payload):
        """Add a new event to the calendar."""
        from backend.services.calendar.calendar_service import CalendarService
        from backend.services.google.google_auth import GoogleAuth

        auth = GoogleAuth()
        service = CalendarService(creds=auth.credentials)

        result = service.create_event(
            summary=payload.get("summary"),
            start_time=payload.get("start_time"),
            end_time=payload.get("end_time"),
            description=payload.get("description", ""),
            location=payload.get("location", ""),
        )
        return result

    # --------------------------------------------------
    # FINANCE TOOLS
    # --------------------------------------------------

    async def ibkr_cancel_order(self, payload):
        order_id = int(payload.get("order_id", 0))
        if order_id <= 0:
            return {"success": False, "error": "Missing or invalid order_id"}

        svc = IBKRService(host="127.0.0.1", port=4002)
        return await asyncio.to_thread(svc.cancel_order, order_id)

    async def ibkr_account_summary(self, payload):
        svc = IBKRService(host="127.0.0.1", port=4002)
        return await asyncio.to_thread(svc.get_account_summary)
        
    async def ibkr_portfolio_summary(self, payload):
        svc = IBKRService(host="127.0.0.1", port=4002)

        account = await asyncio.to_thread(svc.get_account_summary)
        positions = await asyncio.to_thread(svc.get_positions)

        return {
            "success": True,
            "account_summary": account,
            "positions": positions,
        }

    async def ibkr_positions(self, payload):
        svc = IBKRService(host="127.0.0.1", port=4002)
        return await asyncio.to_thread(svc.get_positions)

    async def ibkr_open_orders(self, payload):
        svc = IBKRService(host="127.0.0.1", port=4002)
        return await asyncio.to_thread(svc.get_open_orders)

    async def ibkr_place_paper_order(self, payload):
        symbol = (payload.get("symbol") or "").upper().strip()
        action = (payload.get("action") or "").upper().strip()
        quantity = int(payload.get("quantity", 0))

        if not symbol:
            return {"success": False, "error": "Missing symbol"}
        if action not in {"BUY", "SELL"}:
            return {"success": False, "error": "Action must be BUY or SELL"}
        if quantity <= 0:
            return {"success": False, "error": "Quantity must be greater than zero"}

        svc = IBKRService(host="127.0.0.1", port=4002)
        return await asyncio.to_thread(
            svc.place_stock_market_order,
            symbol,
            action,
            quantity,
        )

    # --------------------------------------------------
    # OTHER TOOLS
    # --------------------------------------------------

    async def summarize_emails(self, payload):
        query = payload.get("query", "is:unread label:inbox")
        count = payload.get("count", 3)
        service = EmailService()
        emails_to_process = []

        try:
            results = (
                service.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=count)
                .execute()
            )

            for msg in results.get("messages", []):
                full_msg = service.get_message(msg["id"])
                if full_msg:
                    headers = full_msg.get("payload", {}).get("headers", [])
                    subject = next(
                        (h["value"] for h in headers if h["name"].lower() == "subject"),
                        "No Subject",
                    )
                    sender = next(
                        (h["value"] for h in headers if h["name"].lower() == "from"),
                        "Unknown",
                    )
                    emails_to_process.append(
                        f"From: {sender}\nSubj: {subject}\nSnippet: {full_msg.get('snippet', '')}"
                    )

            if not emails_to_process:
                return {"summary": "No matching emails found."}

            email_text = "\n---\n".join(emails_to_process)

            from backend.services.email.email_classifier import EmailClassifier

            classifier = EmailClassifier()

            response = classifier.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a personal assistant. Summarize these emails briefly and conversationally.",
                    },
                    {"role": "user", "content": email_text},
                ],
                temperature=0.3,
            )
            return {"summary": response.choices[0].message.content}

        except Exception as e:
            logger.error(f"Summarize tool error: {e}", exc_info=True)
            return {"error": str(e)}

    async def weather(self, payload):
        location = payload.get("location", "Toronto")
        return await self.weather_tool.get_weather(location)

    async def web_search(self, payload):
        query = payload.get("query")
        if not query:
            return {"error": "Missing query"}
        return await search_the_web(query, deep_dive=payload.get("deep_dive", False))

    async def restaurant_search(self, payload):
        cuisine = payload.get("cuisine")
        if not cuisine:
            return {"error": "Cuisine required"}

        query = f"best {cuisine} restaurants in {payload.get('location', 'near me')}"
        search_results = await search_the_web(query)

        if search_results.get("status") == "success":
            return {
                "results": search_results.get("sources"),
                "summary": search_results.get("answer"),
            }

        return search_results

    async def order_food(self, payload):
        return await FoodOrderAgent().place_order(payload)

    async def food_suggest(self, payload):
        return await FoodOrderAgent().suggest(payload.get("cuisine"))

    async def shop_search(self, payload):
        return await ShoppingAgent().search(payload.get("query"))

    async def send_sms(self, payload):
        if not self.twilio_client:
            logger.warning("Twilio disabled — cannot send SMS")
            return {"error": "Twilio disabled"}

        try:
            body = payload.get("body", "")
            to_number = payload.get("to") or settings.owner_number

            logger.info(f"[ToolRouter] Sending SMS to {to_number}")

            msg = await asyncio.to_thread(
                self.twilio_client.messages.create,
                body=body,
                from_=settings.twilio_number_primary,
                to=to_number,
            )

            logger.info(f"[ToolRouter] SMS sent successfully sid={msg.sid}")
            return {"success": True, "sid": msg.sid}

        except Exception as e:
            logger.error(f"[ToolRouter] SMS send failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def reply_email(self, payload):
        service = EmailService()
        result = await asyncio.to_thread(
            service.send_email,
            payload.get("to"),
            payload.get("subject"),
            payload.get("body"),
        )
        return {"success": True, "result": result}

    def chat(self, payload):
        return {"action": "chat", "message": payload.get("message", "")}