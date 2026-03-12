# backend/utils/startup_check.py
from datetime import datetime
from backend.config.settings import settings
from backend.tools.tool_router import ToolRouter
from backend.utils.logger import logger
from backend.services.google.google_auth import GoogleAuth
import asyncio

async def run_startup_check():
    router = ToolRouter()
    issues = []

    logger.info("Running startup self-diagnostic...")

    # 1. Required env vars
    required = ["OPENAI_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "OWNER_NUMBER"]
    missing = [k for k in required if not getattr(settings, k.lower(), None)]
    if missing:
        issues.append(f"Missing env vars: {', '.join(missing)}")

    # 2. Google auth (calendar/email)
    try:
        auth = GoogleAuth()
        if not auth.credentials or not auth.credentials.valid:
            issues.append("Google credentials invalid/expired")
    except Exception as e:
        issues.append(f"Google auth failed: {str(e)[:100]}")

    # 3. Twilio basic check
    if not (settings.twilio_account_sid and settings.twilio_auth_token):
        issues.append("Twilio credentials missing")

    # 4. OpenAI ping (2026 Library Fix)
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        # FIX: Removed 'limit=1' as it is no longer supported in the 2026 SDK
        await client.models.list()  
    except Exception as e:
        issues.append(f"OpenAI connection failed: {str(e)[:100]}")

    # Final status
    status = "OK" if not issues else "WARNING"
    message = (
        f"AI Copilot startup {status} – {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'No issues' if not issues else 'Issues found:'}\n"
        f"{chr(10).join('- ' + i for i in issues) if issues else ''}"
    )

    logger.info(message)

    # Send SMS only on issues (or always if you want)
    if issues or True:  
        try:
            # FIX: Added 'await' so the SMS actually sends to your iPhone
            await router.execute("send_sms", {
                "to": settings.owner_number,
                "body": message[:1400]
            })
            logger.info("Startup status SMS sent")
        except Exception as e:
            logger.error(f"Failed to send startup SMS: {e}")

    return {"status": status, "issues": issues}
