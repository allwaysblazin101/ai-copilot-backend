import pytest

from backend.brain.master_brain import MasterBrain


@pytest.mark.asyncio
async def test_master_brain_finance_balance_query():
    brain = MasterBrain()
    result = await brain.process_query("What's my IBKR balance?", user_id="finance_test_user")

    assert isinstance(result, dict)
    assert "answer" in result
    assert result["metadata"]["intent"] == "finance_account_summary"


@pytest.mark.asyncio
async def test_master_brain_finance_positions_query():
    brain = MasterBrain()
    result = await brain.process_query("What positions do I have?", user_id="finance_test_user")

    assert isinstance(result, dict)
    assert "answer" in result
    assert result["metadata"]["intent"] == "finance_positions"
