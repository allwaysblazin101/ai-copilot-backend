from backend.tools.registry import register_tool


@register_tool(
    name="amazon_search",
    description="Search Amazon products"
)
def search_amazon(payload):

    return [
        {"name": "Laptop", "price": 999},
        {"name": "Mouse", "price": 25}
    ]
