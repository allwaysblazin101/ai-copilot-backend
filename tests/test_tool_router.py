# backend/tests/test_tool_router.py
import pytest
from backend.tools.tool_router import ToolRouter
from backend.utils.logger import logger


@pytest.mark.asyncio
async def test_send_sms_manual_handler():
    logger.info("=== Starting send_sms manual handler test ===")

    router = ToolRouter()
    logger.debug("ToolRouter initialized")

    # Mock payload — invalid number on purpose to test error path safely
    payload = {
        "body": "Test message from AI copilot integration test",
        "to": "test-phone-number"  # invalid → triggers Twilio 21211
    }

    logger.info("Executing send_sms via manual handler")
    result = router.execute("send_sms", payload)

    logger.debug(f"Full send_sms result: {result}")

    # Assertions
    assert isinstance(result, dict)
    assert "error" in result, "Expected an error response from send_sms"

    error_msg = result["error"].lower()
    logger.info(f"Received expected error: {result['error']}")

    # Accept any of these common safe errors
    expected_phrases = [
        "invalid 'to' phone number",          # Twilio 21211
        "twilio client not initialized",      # no creds
        "user confirmation required",         # high-risk block
        "twilio error"                        # generic Twilio fail
    ]

    assert any(phrase in error_msg for phrase in expected_phrases), \
        f"Unexpected error message: {result['error']}. Expected one of: {expected_phrases}"

    print("\n=== send_sms TEST RESULT (expected safe failure) ===")
    print(result)