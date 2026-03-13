from backend.utils.logger import logger


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
        "summarize_emails",
        "weather",
        "ibkr_account_summary",
        "ibkr_positions",
        "ibkr_open_orders",
    }

    def allow(self, tool_name: str) -> bool:
        allowed = tool_name in self.SAFE_TOOLS
        if not allowed:
            logger.warning(f"Tool blocked by safety policy: {tool_name}")
        return allowed