# backend/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
import os
from pathlib import Path


class Settings(BaseSettings):
    # ── Critical ────────────────────────────────────────────────────────────────
    openai_api_key: SecretStr | None = Field(default=None)
    tavily_api_key: SecretStr | None = Field(default=None)
    twilio_account_sid: SecretStr | None = Field(default=None)
    twilio_auth_token: SecretStr | None = Field(default=None)
    twilio_number_primary: str | None = Field(default=None)
    my_phone_number: str | None = Field(default=None)
    owner_number: str | None = Field(default=None)
    stripe_secret_key: SecretStr | None = Field(default=None)
    stripe_publishable_key: str | None = Field(default=None)

    # Google / Gmail
    google_client_secrets_path: str = Field(
        default_factory=lambda: str(Path.home() / "ai-copilot/backend/secrets/credentials.json")
    )

    # Optional services
    polygon_api_key: SecretStr | None = Field(default=None)
    plaid_client_id: str | None = Field(default=None)
    plaid_secret: SecretStr | None = Field(default=None)
    plaid_env: str = Field(default="sandbox")

    # Paths
    secrets_dir: str = Field(
        default_factory=lambda: str(Path.home() / "ai-copilot/backend/secrets")
    )
    log_dir: str = Field(
        default_factory=lambda: str(Path.home() / "ai-copilot/backend/secrets/logs")
    )

    model_config = SettingsConfigDict(
        env_file=os.path.expanduser("~/ai-copilot/backend/secrets/.env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
        env_prefix="",
    )

    def ensure_dirs(self):
        """Create directories if they don't exist."""
        for d in [self.secrets_dir, self.log_dir]:
            os.makedirs(d, exist_ok=True)

    def check_required(self):
        """Raise clear error if critical keys are missing."""
        missing = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.tavily_api_key:
            missing.append("TAVILY_API_KEY") # Added to validation
        if not self.twilio_account_sid or not self.twilio_auth_token:
            missing.append("Twilio credentials (ACCOUNT_SID + AUTH_TOKEN)")
        if missing:
            raise RuntimeError(
                f"Missing required configuration:\n  • " + "\n  • ".join(missing) +
                "\n\nPlease check ~/ai-copilot/backend/secrets/.env"
            )


# Create global instance
settings = Settings()
settings.ensure_dirs()

# Optional: validate critical keys right away
# settings.check_required()
