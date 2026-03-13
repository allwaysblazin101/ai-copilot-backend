import asyncio
from backend.tools.registry import get_tool


async def execute_tool(tool_name, args):
    tool = get_tool(tool_name)

    if not tool:
        return {"error": "Tool not found"}

    func = tool["function"]

    if asyncio.iscoroutinefunction(func):
        return await func(args)

    return func(args)