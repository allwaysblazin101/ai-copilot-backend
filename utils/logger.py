from loguru import logger
import sys
import os

LOG_DIR = os.path.expanduser("~/ai-copilot/backend/secrets/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger.remove()  # remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if os.getenv("DEBUG") else "INFO"
)
logger.add(
    os.path.join(LOG_DIR, "ai_copilot_{time:YYYY-MM-DD}.log"),
    rotation="500 MB",
    retention="10 days",
    level="INFO",
    serialize=False  # human readable
)