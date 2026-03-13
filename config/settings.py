# backend/config/settings.py
import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path.home() / "ai-copilot" / "backend"
SECRETS_DIR = BASE_DIR / "secrets"
LOG_DIR = SECRETS_DIR / "logs"
ENV_FILE = SECRETS_DIR / ".env"


class Settings(BaseSettings):
    # Critical
    openai_api_key: SecretStr | None = Field(default=None)
    tavily_api_key: SecretStr | None = Field(default=None)
    twilio_account_sid: SecretStr | None = Field(default=None)
    twilio_auth_token: SecretStr | None = Field(default=None)
    twilio_number_primary: str | None = Field(default=None)
    my_phone_number: str | None = Field(default=None)
    owner_number: str | None = Field(default=None)
    stripe_secret_key: SecretStr | None = Field(default=None)
    stripe_publishable_key: str | None = Field(default=None)
    ibkr_allow_paper_trading: bool = False

    # Google / Gmail
    google_client_secrets_path: str = Field(
        default_factory=lambda: str(SECRETS_DIR / "credentials.json")
    )

    # Optional services
    polygon_api_key: SecretStr | None = Field(default=None)
    plaid_client_id: str | None = Field(default=None)
    plaid_secret: SecretStr | None = Field(default=None)
    plaid_env: str = Field(default="sandbox")

    # Paths
    secrets_dir: str = Field(default_factory=lambda: str(SECRETS_DIR))
    log_dir: str = Field(default_factory=lambda: str(LOG_DIR))

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
        env_prefix="",
    )

    def ensure_dirs(self):
        """Create runtime directories if they don't exist."""
        for directory in [self.secrets_dir, self.log_dir]:
            os.makedirs(directory, exist_ok=True)

    def check_required(self):
        """Raise clear error if critical keys are missing."""
        missing = []

        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")

        if not self.tavily_api_key:
            missing.append("TAVILY_API_KEY")

        if not self.twilio_account_sid:
            missing.append("TWILIO_ACCOUNT_SID")

        if not self.twilio_auth_token:
            missing.append("TWILIO_AUTH_TOKEN")

        if not self.owner_number:
            missing.append("OWNER_NUMBER")

        if missing:
            raise RuntimeError(
                "Missing required configuration:\n  • "
                + "\n  • ".join(missing)
                + f"\n\nPlease check {ENV_FILE}"
            )


settings = Settings()
settings.ensure_dirs()

# Optional: enable once you want strict startup validation
# settings.check_required()