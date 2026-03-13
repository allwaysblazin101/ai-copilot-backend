import json
import re

from openai import OpenAI

from backend.config.settings import settings
from backend.utils.logger import logger


class EmailClassifier:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key.get_secret_value())

    def classify(self, subject: str, body: str, sender: str = "") -> dict:
        """Classify email and return structured JSON."""
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
            logger.info(
                f"Classifying email: Subject='{subject[:50]}...' From='{sender[:30]}...'"
            )

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )

            content = response.choices[0].message.content.strip()
            content = self._clean_json_response(content)

            classification = json.loads(content)
            logger.debug(f"Email classified: {classification}")
            return classification

        except json.JSONDecodeError:
            logger.error(
                "Invalid JSON from OpenAI classification. Raw content:\n{}",
                content if "content" in locals() else "<no content>",
                exc_info=True,
            )
            return self._fallback_classification()

        except Exception:
            logger.error("Email classification failed", exc_info=True)
            return self._fallback_classification()

    def _clean_json_response(self, content: str) -> str:
        """Strip markdown fences and extract JSON object."""
        content = content.strip()

        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        start = content.find("{")
        end = content.rfind("}")

        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]

        return content.strip()

    def _fallback_classification(self):
        return {
            "category": "OTHER",
            "is_spam_or_ad": False,
            "is_bill_or_invoice": False,
            "is_personal_human": False,
            "priority": "medium",
            "brief_summary": "Classification failed - default applied",
        }