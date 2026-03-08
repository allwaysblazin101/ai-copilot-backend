# backend/tools/registry.py

TOOLS_REGISTRY = {}


def register_tool(name, description, function=None):
    """
    Register tool function
    """

    def decorator(func):
        TOOLS_REGISTRY[name] = {
            "name": name,
            "description": description,
            "function": func
        }
        return func

    if function:
        TOOLS_REGISTRY[name] = {
            "name": name,
            "description": description,
            "function": function
        }
        return function

    return decorator


def get_tool(name):
    return TOOLS_REGISTRY.get(name)


def list_tools():
    return list(TOOLS_REGISTRY.keys())
    

from backend.tools import weather_tool, amazon_tool, walmart_tool, browser_tool, kitchenhub_tool

