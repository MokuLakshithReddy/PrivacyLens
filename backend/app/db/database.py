import aiosqlite
from contextlib import asynccontextmanager
from app.config import settings

CREATE_TABLES_SQL = """
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
    source_start INTEGER,
    source_end INTEGER,
    confidence REAL NOT NULL,
    FOREIGN KEY(policy_id) REFERENCES policies(id)
);
CREATE TABLE IF NOT EXISTS scan_sessions (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'collecting',
    policy_id TEXT,
    FOREIGN KEY(site_id) REFERENCES sites(id)
    ,FOREIGN KEY(policy_id) REFERENCES policies(id)
);
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    scan_session_id TEXT,
    event_id TEXT,
    timestamp INTEGER NOT NULL,
    target_domain TEXT NOT NULL,
    is_third_party INTEGER NOT NULL,
    category TEXT NOT NULL,
    initiator TEXT,
    method TEXT,
    FOREIGN KEY(site_id) REFERENCES sites(id),
    FOREIGN KEY(scan_session_id) REFERENCES scan_sessions(id),
    UNIQUE(scan_session_id, event_id)
);
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    scan_session_id TEXT,
    policy_id TEXT,
    rule_version TEXT NOT NULL DEFAULT 'v1',
    gap_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence REAL NOT NULL,
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(site_id) REFERENCES sites(id),
    FOREIGN KEY(scan_session_id) REFERENCES scan_sessions(id),
    FOREIGN KEY(policy_id) REFERENCES policies(id)
);
CREATE TABLE IF NOT EXISTS risk_snapshots (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    scan_session_id TEXT,
    algorithm_version TEXT NOT NULL DEFAULT 'v1',
    input_summary TEXT NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score INTEGER NOT NULL,
    tier TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence_coverage REAL NOT NULL DEFAULT 0,
    FOREIGN KEY(site_id) REFERENCES sites(id),
    FOREIGN KEY(scan_session_id) REFERENCES scan_sessions(id)
);
"""


async def _ensure_column(db, table: str, column: str, declaration: str) -> None:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in await cursor.fetchall()}
    if column not in existing:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


async def init_db():
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript(CREATE_TABLES_SQL)
        # Additive migrations keep existing local databases readable and safely scoped.
        await _ensure_column(db, "observations", "scan_session_id", "TEXT")
        await _ensure_column(db, "observations", "event_id", "TEXT")
        await _ensure_column(db, "findings", "scan_session_id", "TEXT")
        await _ensure_column(db, "findings", "policy_id", "TEXT")
        await _ensure_column(db, "scan_sessions", "policy_id", "TEXT")
        await _ensure_column(db, "policy_claims", "source_start", "INTEGER")
        await _ensure_column(db, "policy_claims", "source_end", "INTEGER")
        await _ensure_column(db, "findings", "rule_version", "TEXT NOT NULL DEFAULT 'v1'")
        await _ensure_column(db, "risk_snapshots", "scan_session_id", "TEXT")
        await _ensure_column(db, "risk_snapshots", "evidence_coverage", "REAL NOT NULL DEFAULT 0")
        await _ensure_column(db, "risk_snapshots", "algorithm_version", "TEXT NOT NULL DEFAULT 'v1'")
        await _ensure_column(db, "risk_snapshots", "input_summary", "TEXT NOT NULL DEFAULT '{}'")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_observations_scan_event ON observations(scan_session_id, event_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_observations_scan_time ON observations(scan_session_id, timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_policy_site_time ON policies(site_id, retrieved_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_risk_site_time ON risk_snapshots(site_id, timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_scan_site_time ON scan_sessions(site_id, started_at)")
        if settings.retention_days > 0:
            stale = await db.execute(
                "SELECT id FROM sites WHERE last_seen < datetime('now', ?)",
                (f"-{settings.retention_days} days",),
            )
            for row in await stale.fetchall():
                site_id = row[0]
                await db.execute("DELETE FROM observations WHERE site_id = ?", (site_id,))
                await db.execute("DELETE FROM findings WHERE site_id = ?", (site_id,))
                await db.execute("DELETE FROM risk_snapshots WHERE site_id = ?", (site_id,))
                await db.execute("DELETE FROM scan_sessions WHERE site_id = ?", (site_id,))
                await db.execute(
                    "DELETE FROM policy_claims WHERE policy_id IN (SELECT id FROM policies WHERE site_id = ?)",
                    (site_id,),
                )
                await db.execute("DELETE FROM policies WHERE site_id = ?", (site_id,))
                await db.execute("DELETE FROM sites WHERE id = ?", (site_id,))
        await db.commit()


@asynccontextmanager
async def database_connection():
    db = await aiosqlite.connect(settings.sqlite_db_path)
    try:
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
    finally:
        await db.close()


async def get_db():
    async with database_connection() as db:
        db.row_factory = aiosqlite.Row
        yield db
