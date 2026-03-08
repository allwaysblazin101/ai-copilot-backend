# backend/services/google/google_auth.py
import os
import pickle
from urllib.parse import urlparse, parse_qs

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from backend.utils.logger import logger
from backend.config.settings import settings


class GoogleAuth:
    """
    Singleton that handles OAuth for all Google services (Gmail, Calendar, etc.).
    Loads/refreshs/saves token once — everyone else just asks for .credentials
    """
    _instance = None
    _creds = None

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar.events",  # add more scopes later if needed
    ]

    TOKEN_FILE = os.path.join(settings.secrets_dir, "google_token.pickle")
    CLIENT_SECRETS_FILE = os.path.join(settings.secrets_dir, "credentials.json")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GoogleAuth, cls).__new__(cls)
            cls._instance._load_or_authenticate()
        return cls._instance

    def _load_or_authenticate(self):
        creds = None

        if os.path.exists(self.TOKEN_FILE):
            try:
                with open(self.TOKEN_FILE, "rb") as f:
                    creds = pickle.load(f)
                logger.debug("Loaded existing Google OAuth token")
            except Exception as e:
                logger.warning("Failed to load Google token", exc_info=True)

        if creds and creds.valid:
            self._creds = creds
            logger.debug("Google credentials are valid")
            return

        # Try refresh
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Google token refreshed successfully")
                with open(self.TOKEN_FILE, "wb") as f:
                    pickle.dump(creds, f)
                self._creds = creds
                return
            except Exception as e:
                logger.warning("Google token refresh failed — will re-auth", exc_info=True)

        # Full OAuth flow (first time / no refresh token / refresh failed)
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.CLIENT_SECRETS_FILE,
                scopes=self.SCOPES
            )
            flow.redirect_uri = "http://127.0.0.1"

            auth_url, _ = flow.authorization_url(
                access_type="offline",
                prompt="consent"
            )

            logger.info("Google OAuth required — please authorize in browser")
            print("\n=== Authorize Google access ===")
            print("Open this URL in your browser:")
            print(auth_url)
            print("\nAfter approving, paste the FULL redirect URL here (it starts with http://127.0.0.1...)")

            auth_response = input("Redirect URL: ").strip()

            parsed = urlparse(auth_response)
            code = parse_qs(parsed.query).get("code")
            if not code:
                logger.error("No 'code' found in redirect URL")
                raise ValueError("Invalid redirect URL — missing code parameter")

            flow.fetch_token(code=code[0])
            creds = flow.credentials

            with open(self.TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

            logger.success("Google OAuth completed — token saved")
            self._creds = creds

        except Exception as e:
            logger.critical("Google OAuth flow failed completely", exc_info=True)
            self._creds = None

    @property
    def credentials(self) -> Credentials | None:
        """Public access to current credentials."""
        return self._creds

    def is_authenticated(self) -> bool:
        return bool(self._creds and self._creds.valid)