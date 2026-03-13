# backend/api/email_routes.py

from fastapi import APIRouter
from backend.services.email.email_pipeline import EmailPipeline

router = APIRouter()

pipeline = EmailPipeline()


@router.get("/unread")
async def unread_emails():
    result = await pipeline.process_new_email()
    return result