import os
import requests
from backend.tools.registry import register_tool

WALMART_KEY = os.getenv("WALMART_API_KEY")

@register_tool(
    name="walmart_search",
    description="Search Walmart real catalog"
)
def search_walmart(payload):

    query = payload.get("query")

    if not WALMART_KEY:
        return {"error": "Missing Walmart API key"}

    url = "https://api.walmartlabs.com/v1/search"

    params = {
        "query": query,
        "apiKey": WALMART_KEY,
        "numItems": 10
    }

    try:
        res = requests.get(url, params=params, timeout=5)
        return res.json()

    except Exception as e:
        return {"error": str(e)}