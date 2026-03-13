import asyncio

from backend.services.email.email_service import EmailService
from backend.services.email.email_classifier import EmailClassifier
from backend.tools.tool_router import ToolRouter
from backend.utils.logger import logger
from backend.config.settings import settings


class EmailPipeline:
    # Shared instances (init once, reuse)
    _service = None
    _classifier = None
    _tool_router = None

    @classmethod
    def _get_service(cls):
        if cls._service is None:
            cls._service = EmailService()
            logger.debug("EmailService singleton initialized")
        return cls._service

    @classmethod
    def _get_classifier(cls):
        if cls._classifier is None:
            cls._classifier = EmailClassifier()
            logger.debug("EmailClassifier singleton initialized")
        return cls._classifier

    @classmethod
    def _get_tool_router(cls):
        if cls._tool_router is None:
            cls._tool_router = ToolRouter()
            logger.debug("ToolRouter singleton initialized")
        return cls._tool_router

    def __init__(self):
        self.service = self._get_service()
        self.classifier = self._get_classifier()
        self.tool_router = self._get_tool_router()
        self.owner_phone = settings.owner_number or settings.my_phone_number

        if not self.owner_phone:
            logger.warning("No owner_phone configured — SMS notifications disabled")

    async def process_new_email(self):
        logger.info("Starting new email processing cycle")

        emails = self.service.read_unread_emails(max_results=20)

        if not emails:
            logger.info("No new unread emails found")
            return {
                "summary": "No new unread emails",
                "actions_taken": 0,
                "notifications": [],
            }

        actions_taken = 0
        notifications = []
        sms_parts = []

        for email in emails:
            full_body = email["snippet"]

            if len(full_body) < 200:
                full_msg = self.service.get_message(email["id"])
                if full_msg:
                    full_body = full_msg.get("snippet", "") or email["snippet"]

            classification = self.classifier.classify(
                subject=email["subject"],
                body=full_body,
                sender=email["from"],
            )

            category = classification.get("category", "OTHER")
            is_spam = classification.get("is_spam_or_ad", False)
            is_bill = classification.get("is_bill_or_invoice", False)
            is_personal = classification.get("is_personal_human", False)
            brief = classification.get("brief_summary", email["snippet"][:100])

            msg_id = email["id"]

            if is_spam:
                self.service.trash_email(msg_id)
                actions_taken += 1
                logger.info(f"Trashed spam/ad: {email['subject']}")
                continue

            if is_bill or is_personal:
                sms_parts.append(
                    f"[{category}] {email['subject'][:50]}...\n"
                    f"From: {email['from'][:40]}\n"
                    f"{brief}"
                )

            if is_personal:
                self.service.mark_as_read(msg_id)

        if sms_parts:
            message_body = "AI Copilot Alert:\n\n" + "\n\n".join(sms_parts[:5])
            if len(sms_parts) > 5:
                message_body += f"\n\n+ {len(sms_parts) - 5} more important emails"

            logger.info("Sending consolidated SMS notification")
            send_result = await self.tool_router.execute(
                "send_sms",
                {
                    "to": self.owner_phone,
                    "body": message_body,
                },
            )

            notifications.append(send_result)
            logger.debug(f"SMS notification result: {send_result}")

        summary = f"Processed {len(emails)} emails. Trashed {actions_taken} spam/ads."
        logger.info(summary)

        return {
            "summary": summary,
            "actions_taken": actions_taken,
            "notifications": notifications,
            "important_count": len(sms_parts),
        }


if __name__ == "__main__":
    pipeline = EmailPipeline()
    result = asyncio.run(pipeline.process_new_email())
    print("\nPipeline result:", result)