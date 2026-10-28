import os
import shutil
import sqlite3
import aiosqlite
from datetime import datetime
from typing import List, Tuple, Optional
from app.config import settings

MIGRATIONS: List[Tuple[int, str, str, str]] = [
    # (version, name, up_sql, down_sql)
    (
        1,
        "initial_schema",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS sites (
            id TEXT PRIMARY KEY,
            domain TEXT UNIQUE NOT NULL,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS policies (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            url TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_text TEXT NOT NULL,
            FOREIGN KEY(site_id) REFERENCES sites(id)
        );
        CREATE TABLE IF NOT EXISTS policy_claims (
            id TEXT PRIMARY KEY,
            policy_id TEXT NOT NULL,
            category TEXT NOT NULL,
            data_type TEXT NOT NULL,
            purpose TEXT NOT NULL,
            sharing INTEGER NOT NULL,
            third_party TEXT,
            retention_specified INTEGER NOT NULL,
            retention_period TEXT,
            section_name TEXT NOT NULL,
            exact_quote TEXT NOT NULL,
            confidence REAL NOT NULL,
            FOREIGN KEY(policy_id) REFERENCES policies(id)
        );
        CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            target_domain TEXT NOT NULL,
            is_third_party INTEGER NOT NULL,
            category TEXT NOT NULL,
            initiator TEXT,
            method TEXT,
            FOREIGN KEY(site_id) REFERENCES sites(id)
        );
        CREATE TABLE IF NOT EXISTS findings (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            gap_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            confidence REAL NOT NULL,
            title TEXT NOT NULL,
            rationale TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(site_id) REFERENCES sites(id)
        );
        CREATE TABLE IF NOT EXISTS risk_snapshots (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            score INTEGER NOT NULL,
            tier TEXT NOT NULL,
            confidence REAL NOT NULL,
            FOREIGN KEY(site_id) REFERENCES sites(id)
        );
        """,
        """
        DROP TABLE IF EXISTS risk_snapshots;
        DROP TABLE IF EXISTS findings;
        DROP TABLE IF EXISTS observations;
        DROP TABLE IF EXISTS policy_claims;
        DROP TABLE IF EXISTS policies;
        DROP TABLE IF EXISTS sites;
        DROP TABLE IF EXISTS schema_migrations;
        """
    ),
    (
        2,
        "add_storage_and_permission_tables",
        """
        CREATE TABLE IF NOT EXISTS storage_observations (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            is_third_party INTEGER NOT NULL,
            persistent INTEGER NOT NULL,
            byte_length INTEGER,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY(site_id) REFERENCES sites(id)
        );
        CREATE TABLE IF NOT EXISTS permission_observations (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            permission TEXT NOT NULL,
            state TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY(site_id) REFERENCES sites(id)
        );
        """,
        """
        DROP TABLE IF EXISTS permission_observations;
        DROP TABLE IF EXISTS storage_observations;
        """
    )
]

def backup_database(custom_path: Optional[str] = None) -> str:
    """Creates a point-in-time timestamped backup copy of the SQLite database."""
    source = settings.sqlite_db_path
    if not os.path.exists(source):
        # Empty DB, nothing to back up
        return ""

    if custom_path:
        dest = custom_path
    else:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(settings.backup_dir, f"privacylens_backup_{ts}.db")

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    # Using SQLite backup API for online consistency
    src_conn = sqlite3.connect(source)
    dst_conn = sqlite3.connect(dest)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    return dest

def restore_database(backup_path: str) -> bool:
    """Restores database from a validated backup file after integrity verification."""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # Verify backup integrity first
    verify_database_integrity(backup_path)

    # Online restore
    source_conn = sqlite3.connect(backup_path)
    target_conn = sqlite3.connect(settings.sqlite_db_path)
    with target_conn:
        source_conn.backup(target_conn)
    source_conn.close()
    target_conn.close()
    return True

def verify_database_integrity(db_path: Optional[str] = None) -> bool:
    """Executes PRAGMA integrity_check on the specified or active SQLite database."""
    target = db_path or settings.sqlite_db_path
    if not os.path.exists(target):
        return True

    conn = sqlite3.connect(target)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    result = cursor.fetchone()
    conn.close()

    if not result or result[0] != "ok":
        raise ValueError(f"SQLite integrity check failed on {target}: {result}")
    return True

async def run_migrations():
    """Runs all pending forward migrations."""
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        # Create migrations table if not exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );
        """)
        await db.commit()

        cursor = await db.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
        applied = set(row[0] for row in await cursor.fetchall())

        for version, name, up_sql, _ in MIGRATIONS:
            if version not in applied:
                # Create automatic pre-migration backup
                backup_database()
                await db.executescript(up_sql)
                await db.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (version, name)
                )
                await db.commit()

async def rollback_migration(target_version: int):
    """Rolls back applied migrations down to target_version."""
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        cursor = await db.execute("SELECT version FROM schema_migrations ORDER BY version DESC")
        applied_versions = [row[0] for row in await cursor.fetchall()]

        for v in applied_versions:
            if v > target_version:
                migration = next((m for m in MIGRATIONS if m[0] == v), None)
                if migration:
                    _, name, _, down_sql = migration
                    await db.executescript(down_sql)
                    await db.execute("DELETE FROM schema_migrations WHERE version = ?", (v,))
                    await db.commit()

