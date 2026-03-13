# backend/api/sms_routes.py
import logging
import traceback
import asyncio

from fastapi import APIRouter, Request, Form, HTTPException, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from backend.brain.master_brain import MasterBrain
from backend.config.settings import settings
from backend.tools.tool_router import ToolRouter
from backend.services.email.email_service import EmailService
from backend.services.replies.reply_service import ReplyService

logger = logging.getLogger(__name__)


def normalize_phone(number: str | None) -> str:
    if not number:
        return ""
    return "".join(ch for ch in str(number) if ch.isdigit())


router = APIRouter()

try:
    brain = MasterBrain()
except Exception as e:
    logger.error(f"FATAL: MasterBrain failed to initialize: {e}", exc_info=True)
    brain = None

tool_router = ToolRouter()
reply_service = ReplyService()

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

                if "<" in sender:
                    sender = sender.split("<")[0].strip()

                subject = subject[:28]
                sender = sender[:18]

                items.append(f"{i}) {subject} - {sender}")

            body = "Inbox: " + " | ".join(items)

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

    raw_owner_number = settings.owner_number or settings.my_phone_number
    owner_number = normalize_phone(raw_owner_number)
    from_number = normalize_phone(From)

    logger.info(
        f"SMS owner_number={owner_number} from_number={from_number} raw_owner={raw_owner_number} raw_from={From}"
    )

    try:
        # --------------------------------------------------
        # REPLY APPROVAL WORKFLOW
        # --------------------------------------------------
        if owner_number and from_number != owner_number:
            logger.info("Inbound SMS from external sender — creating suggested reply")

            suggested = await reply_service.draft_sms_reply(Body, From)
            await reply_service.save_pending_reply(
                owner_number=owner_number,
                original_sender=From,
                original_message=Body,
                suggested_reply=suggested,
            )

            owner_body = (
                f"Incoming SMS from {From}: {Body[:60]}\n"
                f"Suggested reply: {suggested}\n"
                f"Reply YES to send, EDIT <text> to change, or NO to cancel."
            )
            owner_body = owner_body[:300]

            notify_result = await tool_router.execute(
                "send_sms",
                {
                    "to": raw_owner_number,
                    "body": owner_body,
                },
            )
            logger.info(f"Owner notified of pending SMS reply: {notify_result}")

            reply_text = "Message received."

        elif owner_number and from_number == owner_number:
            pending = await reply_service.get_pending_reply(owner_number)

            if pending and text_lower in {"yes", "send", "approve"}:
                send_result = await tool_router.execute(
                    "send_sms",
                    {
                        "to": pending["original_sender"],
                        "body": pending["suggested_reply"][:140],
                    },
                )
                await reply_service.clear_pending_reply(owner_number)
                logger.info(f"Approved SMS reply sent: {send_result}")
                reply_text = "Approved — reply sent."

            elif pending and text_lower.startswith("edit "):
                edited_reply = Body[5:].strip()
                send_result = await tool_router.execute(
                    "send_sms",
                    {
                        "to": pending["original_sender"],
                        "body": edited_reply[:140],
                    },
                )
                await reply_service.clear_pending_reply(owner_number)
                logger.info(f"Edited SMS reply sent: {send_result}")
                reply_text = "Edited reply sent."

            elif pending and text_lower in {"no", "cancel", "stop"}:
                await reply_service.clear_pending_reply(owner_number)
                reply_text = "Cancelled — I did not send the reply."

            # --------------------------------------------------
            # OWNER'S NORMAL ASSISTANT FLOW
            # --------------------------------------------------
            elif "weather" in text_lower or "temperature" in text_lower or "forecast" in text_lower:
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

            elif "email" in text_lower or "inbox" in text_lower or "mail" in text_lower:
                logger.info("Using async email fallback path")
                asyncio.create_task(send_async_email_summary_sms(From))
                reply_text = "Checking your inbox now. I'll text you the summary in a moment."

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

            elif "ibkr" in text_lower and (
                "balance" in text_lower
                or "buying power" in text_lower
                or "net liquidation" in text_lower
            ):
                logger.info("Using direct IBKR account summary fallback path")

                finance_result = await tool_router.execute("ibkr_account_summary", {})
                logger.info(f"IBKR account summary result: {finance_result}")

                if isinstance(finance_result, dict) and finance_result.get("success"):
                    rows = finance_result.get("account_summary", []) or []
                    wanted = {"NetLiquidation", "TotalCashValue", "BuyingPower"}
                    picked = [r for r in rows if r.get("tag") in wanted]

                    if picked:
                        parts = []
                        for row in picked:
                            parts.append(
                                f"{row.get('tag')}: {row.get('value')} {row.get('currency', '')}".strip()
                            )
                        reply_text = "IBKR: " + " | ".join(parts)
                    else:
                        reply_text = "IBKR is connected, but I couldn't find balance fields."
                else:
                    reply_text = "I couldn't read your IBKR balance right now."

            elif "position" in text_lower or "holdings" in text_lower:
                logger.info("Using direct IBKR positions fallback path")

                finance_result = await tool_router.execute("ibkr_positions", {})
                logger.info(f"IBKR positions result: {finance_result}")

                if isinstance(finance_result, dict) and finance_result.get("success"):
                    positions = finance_result.get("positions", []) or []

                    if not positions:
                        reply_text = "IBKR: no open positions right now."
                    else:
                        parts = []
                        for pos in positions[:3]:
                            parts.append(
                                f"{pos.get('symbol')}: {pos.get('position')} @ {pos.get('avgCost')}"
                            )
                        reply_text = "Positions: " + " | ".join(parts)
                else:
                    reply_text = "I couldn't read your IBKR positions right now."

            elif "open orders" in text_lower or "pending orders" in text_lower or "working orders" in text_lower:
                logger.info("Using direct IBKR open orders fallback path")

                finance_result = await tool_router.execute("ibkr_open_orders", {})
                logger.info(f"IBKR open orders result: {finance_result}")

                if isinstance(finance_result, dict) and finance_result.get("success"):
                    orders = finance_result.get("open_orders", []) or []

                    if not orders:
                        reply_text = "IBKR: no open orders right now."
                    else:
                        parts = []
                        for order in orders[:3]:
                            parts.append(
                                f"{order.get('action')} {order.get('totalQuantity')} {order.get('symbol')} ({order.get('status')})"
                            )
                        reply_text = "Open orders: " + " | ".join(parts)
                else:
                    reply_text = "I couldn't read your IBKR open orders right now."

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
                    reply_text += "\n\n" + "\n".join(suggestions[:2])

            else:
                reply_text = "System Error: Brain not initialized."

        else:
            reply_text = "Owner number not configured."

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