import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from backend.utils.logger import logger
from backend.config.settings import settings

# Load .env with absolute path
env_path = os.path.join(os.path.dirname(__file__), "secrets", ".env")
loaded = load_dotenv(env_path)

logger.info(f"Starting AI Companion API v1.0 - .env loaded: {loaded}")

app = FastAPI(
    title="AI Companion",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

# --- ROUTE REGISTRATION ---
try:
    # 1. AI routes
    from backend.services.ai.ai_service import router as ai_router
    app.include_router(ai_router, prefix="/ai", tags=["AI"])
    logger.debug("[MAIN] AI routes included")

    # 2. Email routes
    from backend.api.email_routes import router as email_router
    app.include_router(email_router, prefix="/email", tags=["Email"])
    logger.debug("[MAIN] Email routes included")

    # 3. SMS routes (Webhook is registered here at /sms/webhook)
    # Note: We use the full backend path to avoid "No module named tools" errors
    from backend.api.sms_routes import router as sms_router
    app.include_router(sms_router, prefix="/sms", tags=["SMS"])
    logger.info("[MAIN] SMS routes included – webhook live at /sms/webhook")

    logger.info("All routes loaded successfully: /ai, /email, /sms")

except ImportError as ie:
    logger.error(f"IMPORT ERROR during route loading: {ie}")
    logger.error("Check backend/api/sms_routes.py and backend/tools/ for internal imports without 'backend.' prefix")
except Exception as e:
    logger.error(f"GENERAL ROUTE LOAD ERROR: {e}")

@app.get("/")
def root():
    return {"status": "online", "service": "AI Companion Core"}
