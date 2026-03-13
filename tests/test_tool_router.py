import pytest

from backend.tools.tool_router import ToolRouter
from backend.utils.logger import logger


@pytest.mark.asyncio
async def test_send_sms_manual_handler():
    logger.info("=== Starting send_sms manual handler test ===")

    router = ToolRouter()
    logger.debug("ToolRouter initialized")

    # Mock payload — invalid number on purpose to test safe failure path
    payload = {
        "body": "Test message from AI copilot integration test",
        "to": "test-phone-number",
    }

    logger.info("Executing send_sms via ToolRouter")
    result = await router.execute("send_sms", payload)

    logger.debug(f"Full send_sms result: {result}")

    assert isinstance(result, dict)
    assert "error" in result or result.get("success") is True

    if "error" in result:
        error_msg = result["error"].lower()
        logger.info(f"Received expected error: {result['error']}")

        expected_phrases = [
            "invalid",
            "twilio disabled",
            "tool blocked",
            "not a valid phone number",
            "unable to create record",
            "authenticate",
        ]

        assert any(phrase in error_msg for phrase in expected_phrases), (
            f"Unexpected error message: {result['error']}. "
            f"Expected one of: {expected_phrases}"
        )
    else:
        logger.info(f"SMS send succeeded unexpectedly in test env: {result}")
        assert result.get("success") is True

    print("\n=== send_sms TEST RESULT ===")
    print(result)