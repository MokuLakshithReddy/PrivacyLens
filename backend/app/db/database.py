import aiosqlite
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
"""

async def init_db():
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()

async def get_db():
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db
