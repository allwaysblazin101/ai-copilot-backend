import os
import importlib

for file in os.listdir(os.path.dirname(__file__)):

    if file.endswith("_tool.py"):

        importlib.import_module(
            f"backend.tools.{file[:-3]}"
        )