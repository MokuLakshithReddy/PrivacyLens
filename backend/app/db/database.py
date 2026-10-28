import aiosqlite
from app.config import settings
from app.db.migrations import run_migrations, verify_database_integrity

async def init_db():
    """Initializes the database and runs all pending schema migrations."""
    await run_migrations()
    verify_database_integrity(settings.sqlite_db_path)

async def get_db():
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db
