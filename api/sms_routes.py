# backend/api/sms_routes.py
import logging
import traceback
import asyncio

from fastapi import APIRouter, Request, Form, HTTPException, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from backend.services.email.email_service import EmailService
from backend.brain.master_brain import MasterBrain
from backend.config.settings import settings
from backend.tools.tool_router import ToolRouter

logger = logging.getLogger(__name__)

router = APIRouter()

try:
    brain = MasterBrain()
except Exception as e:
    logger.error(f"FATAL: MasterBrain failed to initialize: {e}", exc_info=True)
    brain = None

tool_router = ToolRouter()

validator = None
try:
    if settings.twilio_auth_token:
        validator = RequestValidator(settings.twilio_auth_token.get_secret_value())
    else:
        logger.warning("Twilio validator disabled — missing auth token")
except Exception as e:
    logger.error(f"Failed to initialize Twilio validator: {e}", exc_info=True)
    validator = None


async def send_async_email_summary_sms(to_number: str):
    try:
        logger.info(f"Starting background inbox summary for {to_number}")

        service = EmailService()
        emails = await asyncio.to_thread(service.read_unread_emails, 3)

        if not emails:
            body = "Inbox: no unread emails right now."
        else:
            items = []
            for i, email in enumerate(emails[:3], start=1):
                subject = (email.get("subject") or "No subject").replace("\n", " ").strip()
                sender = (email.get("from") or "Unknown").replace("\n", " ").strip()

                # Strip email addresses like <name@example.com>
                if "<" in sender:
                    sender = sender.split("<")[0].strip()

                # Keep each line short
                subject = subject[:28]
                sender = sender[:18]

                items.append(f"{i}) {subject} - {sender}")

            body = "Inbox: " + " | ".join(items)

        # Keep the trial-account SMS safely short
        body = body[:140]

        sms_result = await tool_router.execute(
            "send_sms",
            {
                "to": to_number,
                "body": body,
            },
        )
        logger.info(f"Background inbox SMS sent: {sms_result}")

    except Exception as e:
        logger.error(f"Background email summary SMS failed: {e}", exc_info=True)

@router.post("/webhook")
async def sms_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
):
    if validator is None:
        logger.error("Twilio validator is not configured")
        raise HTTPException(status_code=500, detail="Twilio validator not configured")

    form_data = await request.form()
    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature")

    if not signature or not validator.validate(url, dict(form_data), signature):
        logger.error(f"Unauthorized webhook attempt from {From}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info(f"SMS from {From}: {Body}")

    if len(Body) > 1600:
        Body = Body[:1600] + "..."

    reply_text = "I'm having trouble thinking right now. Please try again."
    text_lower = Body.lower().strip()

    try:
        # Fast path for weather
        if "weather" in text_lower or "temperature" in text_lower or "forecast" in text_lower:
            logger.info("Using direct weather fallback path")
            weather_result = await tool_router.execute("weather", {"location": "Toronto"})

            if isinstance(weather_result, dict) and not weather_result.get("error"):
                temp = weather_result.get("temperature_c")
                location = weather_result.get("location", "your area")
                wind = weather_result.get("wind_kph")

                reply_text = f"Weather for {location}: {temp}°C"
                if wind is not None:
                    reply_text += f", wind {wind} km/h."
                else:
                    reply_text += "."

            else:
                reply_text = "I couldn't get the weather right now."

        # Email path: immediate ack + background SMS
        elif "email" in text_lower or "inbox" in text_lower or "mail" in text_lower:
            logger.info("Using async email fallback path")
            asyncio.create_task(send_async_email_summary_sms(From))
            reply_text = "Checking your inbox now. I'll text you the summary in a moment."

        # Calendar fast path
        elif "schedule" in text_lower or "calendar" in text_lower:
            logger.info("Using direct calendar fallback path")
            calendar_result = await tool_router.execute(
                "calendar_list",
                {"max_results": 5},
            )

            if isinstance(calendar_result, dict):
                if calendar_result.get("summary"):
                    reply_text = calendar_result["summary"]
                elif calendar_result.get("results"):
                    events = calendar_result["results"][:3]
                    lines = []
                    for event in events:
                        summary = event.get("summary", "Untitled")
                        start = event.get("start", "unknown time")
                        lines.append(f"- {summary} at {start}")
                    reply_text = "Upcoming schedule:\n" + "\n".join(lines)
                elif calendar_result.get("error"):
                    reply_text = f"I checked your calendar but hit an error: {calendar_result['error']}"
                else:
                    reply_text = "I checked your calendar but couldn't find anything."
            else:
                reply_text = "I checked your calendar but couldn't find anything."

        # Full brain path
        elif brain:
            logger.info("About to call brain.process_query")
            brain_response = await asyncio.wait_for(
                brain.process_query(Body, user_id=From),
                timeout=12.0,
            )

            reply_text = brain_response.get(
                "answer",
                "I processed that, but have no words.",
            )

            suggestions = brain_response.get("proactive_suggestions", [])
            if suggestions and isinstance(suggestions, list):
                reply_text += "\n\n💡 " + "\n💡 ".join(suggestions)

        else:
            reply_text = "System Error: Brain not initialized."

    except asyncio.TimeoutError:
        logger.error("Brain timed out while processing SMS")
        reply_text = "I'm taking too long to respond right now. Try a simpler request."
    except Exception as e:
        print("\n" + "!" * 20 + " BRAIN CRASH DETECTED " + "!" * 20)
        traceback.print_exc()
        print("!" * 62 + "\n")

        logger.error(f"Brain execution error: {e}", exc_info=True)
        reply_text = "Something went wrong on my end — let's try again?"

    logger.info(f"AI Reply to {From}: {reply_text[:100]}...")

    twiml = MessagingResponse()
    twiml.message(reply_text)

    logger.info("About to return TwiML response to Twilio")

    return Response(
        content=str(twiml),
        media_type="application/xml",
    )