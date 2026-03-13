import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.services.email.email_pipeline import EmailPipeline


@pytest.mark.asyncio
async def test_full_flow():
    print("🚀 Starting Pipeline Sandbox Test...\n")

    # 1. Initialize Pipeline
    EmailPipeline._service = None
    EmailPipeline._classifier = None
    EmailPipeline._tool_router = None
    pipeline = EmailPipeline()

    # 2. Mock the Gmail Service so we don't actually call Google
    mock_emails = [
        {
            "id": "msg_123",
            "from": "bank@alerts.com",
            "subject": "Your Monthly E-Statement is Ready",
            "snippet": "Your bank statement for March is now available for download in the portal.",
        },
        {
            "id": "msg_456",
            "from": "newsletter@techcrunch.com",
            "subject": "The latest in AI and Web3",
            "snippet": "Check out our top stories this week including a deep dive into Tavily vs DDG...",
        },
    ]

    # Inject the mock emails into the pipeline's service
    pipeline.service.read_unread_emails = MagicMock(return_value=mock_emails)

    # Mock message expansion for short snippets
    pipeline.service.get_message = MagicMock(
        side_effect=lambda msg_id: {
            "snippet": next(
                (email["snippet"] for email in mock_emails if email["id"] == msg_id),
                "",
            )
        }
    )

    # Mock the destructive/expensive actions so nothing actually happens
    pipeline.service.trash_email = MagicMock(return_value=True)
    pipeline.service.mark_as_read = MagicMock(return_value=True)

    # Mock classifier so the test is deterministic
    pipeline.classifier.classify = MagicMock(
        side_effect=[
            {
                "category": "FINANCE",
                "is_spam_or_ad": False,
                "is_bill_or_invoice": True,
                "is_personal_human": False,
                "brief_summary": "Your monthly bank statement is ready.",
            },
            {
                "category": "NEWSLETTER",
                "is_spam_or_ad": True,
                "is_bill_or_invoice": False,
                "is_personal_human": False,
                "brief_summary": "Tech newsletter.",
            },
        ]
    )

    # Mock SMS sending so nothing actually goes out
    pipeline.tool_router.execute = AsyncMock(
        return_value={
            "success": True,
            "sid": "mock_sid_123",
        }
    )

    # 3. Run the process
    print("📥 Processing Mock Emails...")
    result = await pipeline.process_new_email()

    print("\n--- TEST RESULTS ---")
    print(f"Summary: {result['summary']}")
    print(f"Important Count: {result['important_count']}")
    print(f"Notifications: {result['notifications']}")

    assert result["important_count"] == 1
    assert result["actions_taken"] == 1
    assert len(result["notifications"]) == 1

    # 4. Manually test ToolRouter web_search path separately
    print("\n🌐 Testing ToolRouter Integration Mock...")
    pipeline.tool_router.execute = AsyncMock(
        return_value={
            "status": "success",
            "answer": "Mock search result for OpenAI GPT-4o-mini latest news.",
            "sources": [],
        }
    )

    search_payload = {
        "query": "Latest news on OpenAI GPT-4o-mini",
        "deep_dive": False,
    }
    search_result = await pipeline.tool_router.execute("web_search", search_payload)

    print(f"Search Status: {search_result.get('status')}")
    if search_result.get("status") == "success":
        print(f"Search Answer: {search_result.get('answer')[:150]}...")
    else:
        print(f"Search Error: {search_result.get('message')}")

    assert search_result["status"] == "success"


if __name__ == "__main__":
    asyncio.run(test_full_flow())