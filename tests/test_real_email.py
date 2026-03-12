import asyncio
from backend.tools.tool_router import ToolRouter

async def test_ai_email_summary():
    router = ToolRouter()
    
    # This triggers the summarize_emails tool in your ToolRouter
    result = await router.execute("summarize_emails", {
        "query": "Uber OR Samsung", 
        "count": 2
    })
    
    if "summary" in result:
        print("\n🤖 AI SUMMARY OF YOUR MAIL:")
        print("-" * 30)
        print(result["summary"])
        print("-" * 30)
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    asyncio.run(test_ai_email_summary())
