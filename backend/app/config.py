import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings:
    app_name = "PrivacyLens API"
    app_version = "1.1.0"
    # Explicit opt-in is required before any policy text leaves the device for AI.
    default_ai_provider = os.getenv("PRIVACYLENS_AI_PROVIDER", "mock").strip().lower()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    deployment_mode = os.getenv("PRIVACYLENS_MODE", "local").strip().lower()
    bind_host = os.getenv("PRIVACYLENS_HOST", "127.0.0.1").strip()
    debug = os.getenv("PRIVACYLENS_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
    sqlite_db_path = os.getenv("PRIVACYLENS_DB_PATH", str(DATA_DIR / "privacylens.db"))
    max_request_bytes = 1_048_576
    retention_days = int(os.getenv("PRIVACYLENS_RETENTION_DAYS", "90"))

    def validate_deployment(self) -> None:
        if self.default_ai_provider not in {"mock", "gemini"}:
            raise RuntimeError("PRIVACYLENS_AI_PROVIDER must be 'mock' or 'gemini'.")
        if self.default_ai_provider == "gemini" and not self.gemini_api_key:
            raise RuntimeError("Gemini mode requires GEMINI_API_KEY.")
        if self.deployment_mode != "local":
            raise RuntimeError(
                "Hosted mode is disabled: authentication, per-user authorization, and quotas "
                "must be implemented before this API can be exposed beyond one local user."
            )
        if self.bind_host not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("Local mode may bind only to loopback. Configure a loopback host.")


settings = Settings()
