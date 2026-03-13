# backend/utils/startup_check.py
from datetime import datetime
import asyncio

from backend.config.settings import settings
from backend.tools.tool_router import ToolRouter
from backend.utils.logger import logger
from backend.services.google.google_auth import GoogleAuth


async def run_startup_check(send_sms_on_success: bool = False):
    router = ToolRouter()
    issues = []

    logger.info("Running startup self-diagnostic...")

    # 1. Required env vars / settings
    required_settings = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
        "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
        "OWNER_NUMBER": settings.owner_number,
    }

    missing = []
    for name, value in required_settings.items():
        if value is None:
            missing.append(name)
            continue

        try:
            # Handle SecretStr safely
            if hasattr(value, "get_secret_value"):
                if not value.get_secret_value():
                    missing.append(name)
            else:
                if not value:
                    missing.append(name)
        except Exception:
            missing.append(name)

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

    # 4. OpenAI ping
    try:
        from openai import AsyncOpenAI

        api_key = settings.openai_api_key
        if hasattr(api_key, "get_secret_value"):
            api_key = api_key.get_secret_value()

        client = AsyncOpenAI(api_key=api_key)
        await client.models.list()
    except Exception as e:
        issues.append(f"OpenAI connection failed: {str(e)[:100]}")

    # Final status
    status = "OK" if not issues else "WARNING"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not issues:
        message = f"AI Copilot startup {status} – {timestamp}\nNo issues"
    else:
        issue_lines = "\n".join(f"- {issue}" for issue in issues)
        message = f"AI Copilot startup {status} – {timestamp}\nIssues found:\n{issue_lines}"

    logger.info(message)

    # Send SMS only if there are issues, unless explicitly requested otherwise
    if issues or send_sms_on_success:
        try:
            result = await router.execute(
                "send_sms",
                {
                    "to": settings.owner_number,
                    "body": message[:1400],
                },
            )
            logger.info(f"Startup status SMS sent: {result}")
        except Exception as e:
            logger.error(f"Failed to send startup SMS: {e}", exc_info=True)

    return {"status": status, "issues": issues}


if __name__ == "__main__":
    result = asyncio.run(run_startup_check())
    print(result)