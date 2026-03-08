from backend.tools.registry import get_tool


def execute_tool(tool_name, args):

    tool = get_tool(tool_name)

    if not tool:
        return {"error": "Tool not found"}

    return tool["function"](args)