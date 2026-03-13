import pytest

from backend.tools.tool_router import ToolRouter


@pytest.mark.asyncio
async def test_ibkr_account_summary_tool():
    router = ToolRouter()
    result = await router.execute("ibkr_account_summary", {})
    assert isinstance(result, dict)
    assert "success" in result


@pytest.mark.asyncio
async def test_ibkr_positions_tool():
    router = ToolRouter()
    result = await router.execute("ibkr_positions", {})
    assert isinstance(result, dict)
    assert "success" in result
