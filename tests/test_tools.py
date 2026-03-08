from backend.tools.registry import list_tools
from backend.tools.tool_executor import execute_tool

import backend.tools  # triggers auto load

print("Loaded Tools:")
print(list_tools())

print(execute_tool("amazon_search", {
    "product": "laptop"
}))