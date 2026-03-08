from backend.tools.registry import register_tool


@register_tool(
    name="kitchenhub_order",
    description="Order food using delivery APIs"
)
def order_food(payload):

    item = payload.get("item")

    return {
        "status": "pending",
        "message": f"Food order created for {item}"
    }
