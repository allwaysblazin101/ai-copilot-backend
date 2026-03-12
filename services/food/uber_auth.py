# backend/services/food/uber_auth.py
"""
Uber Eats API Authentication Helper
Generates fresh access tokens using Client Credentials flow (sandbox or live).
Handles caching of the token and automatic refresh.
"""

import os
import threading
from datetime import datetime, timezone, timedelta
import requests
from dotenv import load_dotenv
from backend.utils.logger import logger

# ────────────────────────────────────────────────
# Load .env explicitly
# ────────────────────────────────────────────────
env_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../secrets/.env")
)
loaded = load_dotenv(env_path)

logger.info(f"UberAuth: Attempted loading .env from {env_path}")
logger.info(f"UberAuth: .env loaded = {loaded}")
logger.info(f"UberAuth: Client ID present = {'yes' if os.getenv('UBER_CLIENT_ID') else 'no'}")
logger.info(f"UberAuth: Client Secret present = {'yes' if os.getenv('UBER_CLIENT_SECRET') else 'no'}")
logger.info(f"UberAuth: Sandbox mode = {os.getenv('UBER_SANDBOX')}")

UBER_CLIENT_ID = os.getenv("UBER_CLIENT_ID")
UBER_CLIENT_SECRET = os.getenv("UBER_CLIENT_SECRET")
UBER_SANDBOX = os.getenv("UBER_SANDBOX", "true").lower() in ("true", "1", "yes")

BASE_URL = "https://sandbox-api.uber.com" if UBER_SANDBOX else "https://api.uber.com"
TOKEN_URL = "https://sandbox-login.uber.com/oauth/v2/token" if UBER_SANDBOX else "https://login.uber.com/oauth/v2/token"

_token_cache = {"access_token": None, "expires_at": None}
_cache_lock = threading.Lock()


def get_uber_token(force_refresh: bool = False) -> str:
    """
    Returns a valid Uber Eats OAuth token using client credentials (sandbox or live).
    Caches the token until it expires.
    """
    global _token_cache
    now = datetime.now(timezone.utc)

    with _cache_lock:
        # Return cached token if still valid
        if (
            not force_refresh
            and _token_cache["access_token"]
            and _token_cache["expires_at"]
            and now < _token_cache["expires_at"]
        ):
            logger.debug("Returning cached Uber token")
            return _token_cache["access_token"]

        if not UBER_CLIENT_ID or not UBER_CLIENT_SECRET:
            raise ValueError("UBER_CLIENT_ID and UBER_CLIENT_SECRET must be set in .env")

        payload = {
            "client_id": UBER_CLIENT_ID,
            "client_secret": UBER_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "eats.order"  # Only eats.order for now
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            logger.info(f"UberAuth: Requesting new {'sandbox' if UBER_SANDBOX else 'live'} token")
            response = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.error(f"UberAuth: {response.status_code} response — {response.text}")

            response.raise_for_status()
            data = response.json()

            access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)

            _token_cache["access_token"] = access_token
            _token_cache["expires_at"] = now + timedelta(seconds=expires_in - 60)  # Refresh 1 min early

            logger.info(
                f"Uber token refreshed (expires in {expires_in}s, sandbox={UBER_SANDBOX})"
            )
            return access_token

        except requests.exceptions.HTTPError as http_err:
            error_text = http_err.response.text if http_err.response else ""
            logger.error(f"UberAuth: HTTP error requesting token — {error_text}")
            raise
        except Exception as e:
            logger.error(f"UberAuth: Unexpected error — {str(e)}")
            raise


# ────────────────────────────────────────────────
# CLI test
# ────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        token = get_uber_token()
        print("\n✅ Uber token generated successfully")
        print(f"Token preview: {token[:30]}...")
        print(f"Length: {len(token)}")
        print(f"Use this token in Authorization header as: Bearer {token}")

    except Exception as e:
        print("\n❌ Failed to generate Uber token")
        print(e)