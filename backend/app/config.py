import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

class Settings(BaseModel):
    app_name: str = "PrivacyLens API"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("PRIVACYLENS_DEBUG", "true").lower() == "true"
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'privacylens.db'}"
    sqlite_db_path: str = str(DATA_DIR / "privacylens.db")
    backup_dir: str = str(BACKUP_DIR)
    
    # AI Provider settings
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    default_ai_provider: str = os.getenv("PRIVACYLENS_AI_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "mock")
    
    # Deployment Security (P1)
    api_key: str = os.getenv("PRIVACYLENS_API_KEY", "")
    require_api_key: bool = os.getenv("PRIVACYLENS_REQUIRE_API_KEY", "false").lower() == "true"
    enforce_loopback_only: bool = os.getenv("PRIVACYLENS_LOOPBACK_ONLY", "true").lower() == "true"
    rate_limit_per_minute: int = int(os.getenv("PRIVACYLENS_RATE_LIMIT", "120"))
    max_payload_bytes: int = int(os.getenv("PRIVACYLENS_MAX_PAYLOAD_BYTES", str(10 * 1024 * 1024))) # 10MB

settings = Settings()
