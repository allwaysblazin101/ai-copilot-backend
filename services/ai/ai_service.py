from fastapi import APIRouter
from pydantic import BaseModel

from backend.brain.engine import BrainEngine
from backend.services.email.email_service import EmailService

router = APIRouter()

brain = BrainEngine()
email_service = EmailService()


# -----------------------------
# Request Model
# -----------------------------

class ChatRequest(BaseModel):
    message: str


# -----------------------------
# AI Chat Endpoint
# -----------------------------

@router.post("/chat")
async def chat(request: ChatRequest):

    result = await brain.think(request.message)

    return {
        "input": request.message,
        "brain_result": result
    }


# -----------------------------
# Email Reply Endpoint
# -----------------------------

class EmailRequest(BaseModel):
    to_email: str
    message: str


@router.post("/email/reply")
async def email_reply(request: EmailRequest):

    try:

        response = await brain.think(request.message)

        subject = "AI Reply"
        body = f"""
AI Generated Reply

{response}

Best regards
AI Copilot
"""

        email_service.send_email(
            request.to_email,
            subject,
            body
        )

        return {"status": "email_sent"}

    except Exception as e:

        return {"error": str(e)}