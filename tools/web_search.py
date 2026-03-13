# backend/tools/web_search.py
import aiohttp

from backend.config.settings import settings
from backend.utils.logger import logger


async def search_the_web(query: str, deep_dive: bool = False):
    """
    Tavily Search Tool.
    Uses Bearer auth and returns a compact normalized result.
    """
    if not query or not str(query).strip():
        return {"status": "error", "message": "Missing search query"}

    if not settings.tavily_api_key:
        logger.error("TAVILY_API_KEY missing in settings")
        return {"status": "error", "message": "Search key not configured"}

    api_key = settings.tavily_api_key.get_secret_value()
    url = "https://api.tavily.com/search"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": query,
        "search_depth": "advanced" if deep_dive else "basic",
        "include_answer": True,
        "max_results": 5,
    }

    timeout = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.success(f"Web search successful for: {query}")

                    results = data.get("results", []) or []
                    normalized_sources = [
                        {
                            "title": item.get("title"),
                            "url": item.get("url"),
                            "content": item.get("content"),
                        }
                        for item in results[:3]
                    ]

                    return {
                        "status": "success",
                        "answer": data.get("answer"),
                        "sources": normalized_sources,
                    }

                error_text = await resp.text()
                logger.error(f"Tavily API {resp.status}: {error_text}")
                return {
                    "status": "error",
                    "message": f"Search failed: {resp.status}",
                    "details": error_text[:500],
                }

    except Exception as e:
        logger.error(f"Web Search Tool Exception: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Search engine connection failed.",
            "details": str(e),
        }