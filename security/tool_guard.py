class ToolGuard:
    SAFE_TOOLS = {
    "chat",
    "send_sms",
    "shop_search",
    "food_suggest",
    "amazon_search",
    "web_search",
    "order_food",
    "restaurant_search",
    "create_calendar_event",
    "calendar_list",
    "reply_email",
}
    

    def reply_email(self, payload): # Ensure this is indented exactly like 'execute'
        try:
            service = EmailService()
            service.send_email(
                to=payload.get("to"),
                subject=payload.get("subject", "AI Reply"),
                body=payload.get("body", "")
            )
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}


    def allow(self, tool_name):
        allowed = tool_name in self.SAFE_TOOLS
        if not allowed:
            from backend.utils.logger import logger
            logger.warning(f"Tool blocked by safety policy: {tool_name}")
        return allowed