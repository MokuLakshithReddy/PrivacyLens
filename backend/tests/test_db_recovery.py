import os
import tempfile
import pytest
import sqlite3
import aiosqlite
from app.config import settings
from app.db.migrations import (
    run_migrations,
    rollback_migration,
    backup_database,
    restore_database,
    verify_database_integrity
)

@pytest.mark.asyncio
async def test_database_migrations_and_recovery():
    # 1. Run migrations
    await run_migrations()
    assert verify_database_integrity(settings.sqlite_db_path) is True

    # 2. Insert test site record
    test_site_id = "test_recovery_site"
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO sites (id, domain) VALUES (?, ?)",
            (test_site_id, "recovery-test.org")
        )
        await db.commit()

    # 3. Create point-in-time backup
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_backup:
        backup_file = tmp_backup.name

    try:
        backed_up_path = backup_database(custom_path=backup_file)
        assert os.path.exists(backed_up_path)
        assert verify_database_integrity(backed_up_path) is True

        # 4. Simulate corruption or accidental deletion
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            await db.execute("DELETE FROM sites WHERE id = ?", (test_site_id,))
            await db.commit()

        # Verify deletion
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            cursor = await db.execute("SELECT * FROM sites WHERE id = ?", (test_site_id,))
            assert await cursor.fetchone() is None

        # 5. Restore database from backup
        restore_result = restore_database(backed_up_path)
        assert restore_result is True

        # Verify restored record
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            cursor = await db.execute("SELECT domain FROM sites WHERE id = ?", (test_site_id,))
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "recovery-test.org"

        # 6. Test Migration Rollback down to Version 1
        await rollback_migration(target_version=1)
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            cursor = await db.execute("SELECT version FROM schema_migrations")
            versions = [r[0] for r in await cursor.fetchall()]
            assert 2 not in versions
            assert 1 in versions

        # Re-apply migrations
        await run_migrations()
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            cursor = await db.execute("SELECT version FROM schema_migrations")
            versions = [r[0] for r in await cursor.fetchall()]
            assert 2 in versions

    finally:
        if os.path.exists(backup_file):
            os.remove(backup_file)
