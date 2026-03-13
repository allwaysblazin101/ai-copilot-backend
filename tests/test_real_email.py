import pytest

from backend.services.email.email_pipeline import EmailPipeline


@pytest.mark.asyncio
async def test_ai_email_summary():
    # Reset shared singleton state so mocks from other tests do not leak in
    EmailPipeline._service = None
    EmailPipeline._classifier = None
    EmailPipeline._tool_router = None

    pipeline = EmailPipeline()
    result = await pipeline.process_new_email()

    print(result)

    assert isinstance(result, dict)
    assert "summary" in result