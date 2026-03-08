import os
import pathlib
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar"
]

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CREDENTIAL_PATH = BASE_DIR / "secrets/credentials.json"
TOKEN_PATH = BASE_DIR / "secrets/token.json"


def get_flow():
    return InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIAL_PATH),
        SCOPES
    )


def authenticate():
    """Run once to generate token.json"""
    flow = get_flow()

    creds = flow.run_local_server(
        port=0,
        prompt="consent"
    )

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    return creds


def load_credentials():
    """Load existing credentials or re-auth"""
    if TOKEN_PATH.exists():
        return Credentials.from_authorized_user_file(
            str(TOKEN_PATH),
            SCOPES
        )

    return authenticate()