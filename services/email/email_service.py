# backend/services/email/email_service.py
import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from backend.services.google.google_auth import GoogleAuth
from backend.utils.logger import logger


class EmailService:
    def __init__(self, enable_auth=True):
        self.service = None

        if not enable_auth:
            logger.info("EmailService initialized without auth (mock mode)")
            return

        # Get shared credentials from GoogleAuth (handles OAuth, refresh, token storage)
        google_auth = GoogleAuth()
        creds = google_auth.credentials

        if creds:
            self.service = build("gmail", "v1", credentials=creds)
            logger.success("Gmail API service initialized successfully")
        else:
            logger.warning("No Google credentials available — Gmail disabled")

    def get_message(self, message_id: str):
        """Fetch full message data by ID (used by pipeline for detailed body)."""
        if not self.service:
            logger.warning("Gmail service not initialized — cannot fetch message")
            return None

        try:
            msg_data = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()
            logger.debug(f"Fetched full message ID: {message_id}")
            return msg_data
        except Exception as e:
            logger.error(f"Failed to fetch message {message_id}", exc_info=True)
            return None

    def trash_email(self, message_id: str) -> bool:
        """Move an email to Trash by ID."""
        if not self.service:
            logger.warning("Gmail service not available — cannot trash email")
            return False

        try:
            self.service.users().messages().trash(
                userId="me",
                id=message_id
            ).execute()
            logger.info(f"Email {message_id} moved to Trash")
            return True
        except Exception as e:
            logger.error(f"Failed to trash email {message_id}", exc_info=True)
            return False

    def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read (remove UNREAD label)."""
        if not self.service:
            logger.warning("Gmail service not available — cannot mark as read")
            return False

        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.info(f"Email {message_id} marked as read")
            return True
        except Exception as e:
            logger.error(f"Failed to mark email {message_id} as read", exc_info=True)
            return False

    def read_unread_emails(self, max_results=10):
        if not self.service:
            logger.warning("Gmail service not available — returning empty inbox")
            return []

        try:
            results = self.service.users().messages().list(
                userId="me",
                q="is:unread label:inbox",
                maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} unread inbox messages")

            output = []

            for msg in messages:
                msg_data = self.get_message(msg["id"])
                if not msg_data:
                    continue

                headers = msg_data.get("payload", {}).get("headers", [])

                subject = next(
                    (h["value"] for h in headers if h["name"].lower() == "subject"),
                    "No subject"
                )

                sender = next(
                    (h["value"] for h in headers if h["name"].lower() == "from"),
                    "Unknown"
                )

                output.append({
                    "id": msg["id"],
                    "subject": subject,
                    "from": sender,
                    "snippet": msg_data.get("snippet", "")
                })

            return output

        except Exception as e:
            logger.error("Failed to read unread emails", exc_info=True)
            return []

    def send_email(self, to_email, subject, body):
        if not self.service:
            logger.warning("Gmail service not available — cannot send email")
            return False

        try:
            msg = MIMEText(body)
            msg["to"] = to_email
            msg["subject"] = subject

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            self.service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}", exc_info=True)
            return False