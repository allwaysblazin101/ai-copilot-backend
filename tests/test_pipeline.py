import asyncio
from unittest.mock import MagicMock
from backend.services.email.email_pipeline import EmailPipeline
from backend.services.email.email_service import EmailService

async def test_full_flow():
    print("🚀 Starting Pipeline Sandbox Test...\n")
    
    # 1. Initialize Pipeline
    pipeline = EmailPipeline()
    
    # 2. Mock the Gmail Service so we don't actually call Google
    mock_emails = [
        {
            "id": "msg_123",
            "from": "bank@alerts.com",
            "subject": "Your Monthly E-Statement is Ready",
            "snippet": "Your bank statement for March is now available for download in the portal."
        },
        {
            "id": "msg_456",
            "from": "newsletter@techcrunch.com",
            "subject": "The latest in AI and Web3",
            "snippet": "Check out our top stories this week including a deep dive into Tavily vs DDG..."
        }
    ]
    
    # Inject the mock emails into the pipeline's service
    pipeline.service.read_unread_emails = MagicMock(return_value=mock_emails)
    
    # Mock the destructive/expensive actions so nothing actually happens
    pipeline.service.trash_email = MagicMock(return_value=True)
    pipeline.service.mark_as_read = MagicMock(return_value=True)
    
    # 3. Run the process
    print("📥 Processing Mock Emails...")
    result = pipeline.process_new_email()
    
    print("\n--- TEST RESULTS ---")
    print(f"Summary: {result['summary']}")
    print(f"Important Count: {result['important_count']}")
    
    # 4. Manually test the Tavily Search via ToolRouter
    print("\n🌐 Testing Tavily Integration via ToolRouter...")
    search_payload = {"query": "Latest news on OpenAI GPT-4o-mini", "deep_dive": False}
    search_result = await pipeline.tool_router.execute("web_search", search_payload)
    
    print(f"Search Status: {search_result.get('status')}")
    if search_result.get('status') == 'success':
        print(f"Tavily Answer: {search_result.get('answer')[:150]}...")
    else:
        print(f"Search Error: {search_result.get('message')}")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
