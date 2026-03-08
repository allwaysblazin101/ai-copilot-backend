import logging
import os

LOG_FILE = "backend/secrets/ai_system.log"

os.makedirs("backend/secrets", exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)


class AILogger:

    @staticmethod
    def log_event(event):
        logging.info(event)

    @staticmethod
    def log_error(error):
        logging.error(error)