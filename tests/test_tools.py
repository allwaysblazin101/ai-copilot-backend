#backend/tests/test_tools.py
import pytest

from backend.tools.registry import list_tools
from backend.tools.tool_executor import execute_tool

import backend.tools  # triggers auto load


def test_tools_registry_loads():
    tools = list_tools()

    print("Loaded Tools:")
    print(tools)

    assert tools is not None
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_amazon_search_tool_executes():
    result = await execute_tool("amazon_search", {"product": "laptop"})

    print(result)

    assert result is not None