# backend/tools/web_search.py
import aiohttp
from backend.config.settings import settings
from backend.utils.logger import logger

async def search_the_web(query: str, deep_dive: bool = False):
    """
    Tavily Search Tool.
    Fixed 405 error by using exact URL and Bearer Token header.
    """
    if not settings.tavily_api_key:
        logger.error("❌ TAVILY_API_KEY missing in settings")
        return {"status": "error", "message": "Search key not configured"}

    api_key = settings.tavily_api_key.get_secret_value()
    
    # Audit Fix: Ensure NO trailing slash at the end of the URL
    url = "https://api.tavily.com/search"
    
    # Audit Fix: Tavily requires 'Authorization: Bearer <token>'
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": query,
        "search_depth": "advanced" if deep_dive else "basic",
        "include_answer": True,
        "max_results": 5
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Audit Fix: Use uppercase POST and no redirect-prone trailing slash
            async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.success(f"🌐 Web search successful for: {query}")
                    return {
                        "status": "success",
                        "answer": data.get("answer"),
                        "sources": [res.get("url") for res in data.get("results", [])[:3]]
                    }
                
                # Capture exact error detail to stop 405/401 loops
                error_text = await resp.text()
                logger.error(f"❌ Tavily API {resp.status}: {error_text}")
                return {"status": "error", "message": f"Search failed: {resp.status}"}

    except Exception as e:
        logger.error(f"⚠️ Web Search Tool Exception: {e}")
        return {"status": "error", "message": "Search engine connection failed."}
