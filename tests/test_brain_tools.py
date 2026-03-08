# backend/tests/test_brain_tools.py
import pytest
from backend.brain.master_brain import MasterBrain
from backend.utils.logger import logger


@pytest.mark.asyncio
async def test_tool_amazon_search():
    logger.info("=== Starting amazon_search tool integration test ===")

    brain = MasterBrain()
    logger.debug("MasterBrain initialized successfully")

    context = {
        "tool": "amazon_search",
        "tool_args": {
            "product": "paper towels"
        }
    }

    user_message = "Find paper towels"
    logger.info(f"Sending message to brain: '{user_message}'")
    logger.debug(f"With context: {context}")

    try:
        result = await brain.think(user_message, context)
        logger.success("brain.think() completed without exception")

        # Basic structural checks
        assert "reply_text" in result, "Response missing 'reply_text'"
        assert isinstance(result["reply_text"], str), "'reply_text' should be a string"
        assert "tool_result" in result, "Response missing 'tool_result'"

        logger.info(f"AI reply: {result['reply_text'][:200]}{'...' if len(result['reply_text']) > 200 else ''}")
        logger.info(f"Tool result: {result.get('tool_result')}")

        print("\n=== AMAZON SEARCH TEST RESULT ===")
        print(result)

    except Exception as e:
        logger.error("Test failed during amazon_search", exc_info=True)
        raise


@pytest.mark.asyncio
async def test_create_calendar_event():
    logger.info("=== Starting create_calendar_event tool integration test ===")

    brain = MasterBrain()
    logger.debug("MasterBrain initialized successfully")

    context = {
        "tool": "create_calendar_event",
        "tool_args": {
            "summary": "Test Meeting with Grok",
            "start": "tomorrow at 3pm",
            "end": "tomorrow at 4pm"  # optional but recommended
        }
    }

    user_message = "Schedule a test meeting tomorrow at 3pm"
    logger.info(f"Sending message to brain: '{user_message}'")
    logger.debug(f"With context: {context}")

    try:
        result = await brain.think(user_message, context)
        logger.success("brain.think() completed without exception")

        # Basic assertions
        assert "reply_text" in result, "Response missing 'reply_text'"
        assert "tool_result" in result, "Response missing 'tool_result'"
        assert isinstance(result["tool_result"], dict), "tool_result should be a dict"

        # Check if creation succeeded
        tool_result = result["tool_result"]
        if "success" in tool_result:
            logger.success(f"Event created! ID: {tool_result.get('event_id')}")
        else:
            logger.warning(f"Event creation returned: {tool_result}")

        logger.info(f"AI reply: {result['reply_text'][:200]}{'...' if len(result['reply_text']) > 200 else ''}")
        logger.info(f"Tool result: {tool_result}")

        print("\n=== CREATE CALENDAR EVENT TEST RESULT ===")
        print(result)

    except Exception as e:
        logger.error("Test failed during create_calendar_event", exc_info=True)
        raise