import pytest
from app.db.database import init_db

@pytest.fixture(autouse=True)
async def initialize_test_database():
    await init_db()
