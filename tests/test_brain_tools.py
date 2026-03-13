import pytest

from backend.brain.master_brain import MasterBrain
from backend.utils.logger import logger


@pytest.mark.asyncio
async def test_tool_amazon_search():
    logger.info("=== Starting amazon_search tool integration test ===")

    brain = MasterBrain()
    logger.debug("MasterBrain initialized successfully")

    user_message = "Find paper towels"
    logger.info(f"Sending message to brain: '{user_message}'")

    result = await brain.process_query(user_message, user_id="test_user")

    logger.debug(f"Brain result: {result}")

    assert isinstance(result, dict)
    assert "answer" in result


@pytest.mark.asyncio
async def test_create_calendar_event():
    logger.info("=== Starting create_calendar_event tool integration test ===")

    brain = MasterBrain()
    logger.debug("MasterBrain initialized successfully")

    user_message = "Schedule a test meeting tomorrow at 3pm"
    logger.info(f"Sending message to brain: '{user_message}'")

    result = await brain.process_query(user_message, user_id="test_user")

    logger.debug(f"Brain result: {result}")

    assert isinstance(result, dict)
    assert "answer" in result