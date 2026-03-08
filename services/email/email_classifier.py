# backend/services/email/email_classifier.py
from openai import OpenAI
import json
import os

from backend.utils.logger import logger
from backend.config.settings import settings


class EmailClassifier:
    def __init__(self):
        # Get API key from centralized settings (no more os.getenv)
        api_key = settings.openai_api_key
        if not api_key:
            logger.error("OPENAI_API_KEY missing in settings — email classification will fail")
            raise ValueError("OPENAI_API_KEY not found in configuration")

        self.client = OpenAI(api_key=api_key.get_secret_value())
        logger.debug("OpenAI client initialized for email classification")

    def classify(self, subject: str, body: str, sender: str = "") -> dict:
        """Classify email and return structured JSON"""
        prompt = f"""
        Analyze this email for my personal AI assistant:

        From: {sender}
        Subject: {subject}
        Body preview: {body[:1000]}

        Return ONLY valid JSON (no extra text):

        {{
          "category": "PERSONAL | BILL_FINANCE | SPAM_ADS | NEWSLETTER | PROMOTION | OTHER",
          "is_spam_or_ad": true or false,
          "is_bill_or_invoice": true or false,
          "is_personal_human": true or false,
          "priority": "high" or "medium" or "low",
          "brief_summary": "one short sentence summary"
        }}
        """

        try:
            logger.info(f"Classifying email: Subject='{subject[:50]}...' From='{sender[:30]}...'")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            content = response.choices[0].message.content.strip()

            # Parse JSON safely
            classification = json.loads(content)
            logger.debug(f"Email classified: {classification}")
            return classification

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from OpenAI classification: {content}", exc_info=True)
            return self._fallback_classification()

        except Exception as e:
            logger.error("Email classification failed", exc_info=True)
            return self._fallback_classification()

    def _fallback_classification(self):
        """Safe default if classification fails"""
        return {
            "category": "OTHER",
            "is_spam_or_ad": False,
            "is_bill_or_invoice": False,
            "is_personal_human": False,
            "priority": "medium",
            "brief_summary": "Classification failed - default applied"
        }