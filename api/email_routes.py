from fastapi import APIRouter
from backend.services.email.email_pipeline import EmailPipeline

router = APIRouter()

pipeline = EmailPipeline()


@router.get("/unread")
def unread_emails():
    return pipeline.process_new_email()