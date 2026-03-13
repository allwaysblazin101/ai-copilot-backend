import importlib
from pathlib import Path

tools_dir = Path(__file__).parent

for path in sorted(tools_dir.iterdir()):
    if path.is_file() and path.name.endswith("_tool.py"):
        importlib.import_module(f"backend.tools.{path.stem}")