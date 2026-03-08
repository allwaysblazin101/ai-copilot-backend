import os
from dotenv import load_dotenv
from backend.services.email.email_service import EmailService


def test_real_email_read():

    load_dotenv("backend/secrets/.env")

    # Only verify env exists
    # Do NOT run real OAuth during CI tests

    assert os.getenv("EMAIL_USER") is not None
    assert os.getenv("EMAIL_PASS") is not None

    # Disable auth for test safety
    service = EmailService(enable_auth=False)

    emails = service.read_unread_emails()

    assert isinstance(emails, list)

    print("\nLatest Emails:")
    for mail in emails:
        print(mail.get("subject"))
