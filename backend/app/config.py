import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings(BaseModel):
    app_name: str = "PrivacyLens API"
    app_version: str = "1.0.0"
    debug: bool = True
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'privacylens.db'}"
    sqlite_db_path: str = str(DATA_DIR / "privacylens.db")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    default_ai_provider: str = os.getenv("PRIVACYLENS_AI_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "mock")

settings = Settings()
