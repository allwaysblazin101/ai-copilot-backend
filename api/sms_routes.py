# backend/api/sms_routes.py
import logging
import traceback
from fastapi import APIRouter, Request, Form, HTTPException, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from backend.brain.master_brain import MasterBrain
from backend.config.settings import settings

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize the brain once so it maintains session state
# Ensure MasterBrain() __init__ doesn't crash on startup
try:
    brain = MasterBrain()
except Exception as e:
    logger.error(f"FATAL: MasterBrain failed to initialize: {e}")
    traceback.print_exc()
    brain = None

# Initialize Twilio Validator for security
validator = RequestValidator(settings.twilio_auth_token.get_secret_value())

@router.post("/webhook")
async def sms_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...)
):
    # 1. ⭐ Security: Verify Twilio signature
    form_data = await request.form()
    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature")

    # Important: dict(form_data) is required for the validator
    if not signature or not validator.validate(url, dict(form_data), signature):
        logger.error(f"⚠️ Unauthorized webhook attempt from {From}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info(f"📩 SMS from {From}: {Body}")

    # 2. ⭐ Safety: Truncate very long messages
    if len(Body) > 1600:
        Body = Body[:1600] + "..."

    # Default fallback message
    reply_text = "I'm having trouble thinking right now. Please try again."

    # 3. ⭐ Process with MasterBrain
    if not brain:
        reply_text = "System Error: Brain not initialized."
    else:
        try:
            # Request the brain to process the query
            # We use process_query to match the superior MasterBrain architecture
            brain_response = await brain.process_query(Body, user_id=From)
            
            # Extract the main text answer
            reply_text = brain_response.get("answer", "I processed that, but have no words.")
            
            # Append proactive suggestions if the brain generated any
            suggestions = brain_response.get("proactive_suggestions", [])
            if suggestions and isinstance(suggestions, list):
                reply_text += "\n\n💡 " + "\n💡 ".join(suggestions)

        except Exception as e:
            # THIS IS KEY: It prints the EXACT error to your terminal so you can fix it
            print("\n" + "!"*20 + " BRAIN CRASH DETECTED " + "!"*20)
            traceback.print_exc() 
            print("!"*62 + "\n")
            
            logger.error(f"❌ Brain execution error: {e}")
            reply_text = "Something went wrong on my end — let's try again?"

    logger.info(f"🤖 AI Reply to {From}: {reply_text[:100]}...")

    # 4. ⭐ Format TwiML response for Twilio
    twiml = MessagingResponse()
    twiml.message(reply_text)

    # Return as application/xml so Twilio recognizes the response
    return Response(
        content=str(twiml), 
        media_type="application/xml"
    )
