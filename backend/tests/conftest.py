import pytest
from app.config import settings
from app.db.database import init_db


@pytest.fixture(autouse=True)
async def initialize_test_database(tmp_path, monkeypatch):
    # Every test gets its own database; no state leaks between runs.
    monkeypatch.setattr(settings, "sqlite_db_path", str(tmp_path / "privacylens-test.db"))
    await init_db()
