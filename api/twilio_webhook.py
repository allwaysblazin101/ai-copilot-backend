# backend/api/twilio_webhook.py
from fastapi import APIRouter, Request, Response, HTTPException
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from backend.brain.master_brain import MasterBrain
from backend.utils.logger import logger
from backend.config.settings import settings

router = APIRouter()
brain = MasterBrain()

@router.post("/sms")
async def receive_sms(request: Request):
    """
    Hardened Twilio Webhook: Validates signatures and verifies the owner.
    """
    # 1. TWILIO SIGNATURE VALIDATION (Anti-Spoofing)
    validator = RequestValidator(settings.twilio_auth_token.get_secret_value())
    
    url = str(request.url)
    if "http://" in url and not url.startswith("http://localhost"):
        url = url.replace("http://", "https://")  # Fixes proxy/GoDaddy SSL issues

    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature")

    if not signature or not validator.validate(url, dict(form_data), signature):
        logger.error("🚨 SECURITY ALERT: Invalid Twilio Signature detected!")
        return Response(content="Forbidden", status_code=403)

    # 2. OWNER WHITELIST
    sender = form_data.get("From")
    incoming_msg = form_data.get("Body", "").strip()

    if settings.owner_number and sender != settings.owner_number:
        logger.warning(f"🚫 Unauthorized access attempt from {sender}")
        return Response(content="Unauthorized", status_code=403)

    logger.info(f"📲 Verified SMS from {sender}: {incoming_msg}")

    # ────────────────────────────────────────────────
    # FIXED: Build proper context so IntentRouter can detect tools
    # ────────────────────────────────────────────────
    context = {
        "sender": sender,
        "sentiment": 0.7,           # or compute real sentiment if you have it
        # Let the brain's IntentRouter decide what tool (if any) to use
    }

    # Process with full brain (this will now trigger web_search for weather)
    result = await brain.think(incoming_msg, context=context)

    reply = result.get("reply_text", "Sorry, I couldn't process that right now.")

    # Optional: log the full result for debugging
    logger.info(f"AI generated reply: {reply[:200]}{'...' if len(reply) > 200 else ''}")

    # 4. SECURE XML RESPONSE
    twilio_resp = MessagingResponse()
    
    # Safety cap (Twilio segment limit ~1600 chars, but we keep it shorter)
    safe_reply = (reply[:1200] + " [...] (message truncated)") if len(reply) > 1200 else reply
    twilio_resp.message(safe_reply)

    return Response(content=str(twilio_resp), media_type="application/xml")