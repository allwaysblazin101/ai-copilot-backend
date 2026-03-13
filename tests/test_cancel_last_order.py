import asyncio

from backend.services.replies.reply_service import ReplyService
from backend.tools.tool_router import ToolRouter

OWNER = "14166971728"  # replace if needed with your digits-only owner number


async def main():
    reply_service = ReplyService()
    tool_router = ToolRouter()

    last_order = await reply_service.get_last_order(OWNER)
    print("LAST ORDER RECORD:", last_order)

    if not last_order:
        print("No saved last order found.")
        return

    result = last_order.get("order_result", {}) or {}
    submitted = result.get("submitted_order", {}) or {}
    order_id = int(submitted.get("orderId", 0))

    if order_id <= 0:
        print("No valid orderId found in saved last order.")
        return

    cancel_result = await tool_router.execute(
        "ibkr_cancel_order",
        {"order_id": order_id},
    )
    print("CANCEL RESULT:", cancel_result)


if __name__ == "__main__":
    asyncio.run(main())