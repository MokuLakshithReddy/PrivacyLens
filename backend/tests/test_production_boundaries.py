from pathlib import Path
from unittest.mock import AsyncMock
import asyncio

import aiosqlite
import pytest

from app.core.policy_fetcher import MAX_POLICY_BYTES, PolicyFetchError, PublicResolver, fetch_public_policy, normalize_policy_url
from app.db.database import init_db


def test_storage_inspector_never_reads_values_or_cookie_names():
    source = Path(__file__).parents[2] / "extension" / "src" / "content" / "storage-inspector.ts"
    text = source.read_text(encoding="utf-8")
    assert ".getItem(" not in text
    assert ".key(" not in text
    assert "document.cookie" not in text
    assert "window.localStorage.length" in text
    assert "window.sessionStorage.length" in text


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com/privacy",
    "http://localhost/privacy", "http://127.0.0.1/privacy",
    "http://10.1.2.3/privacy", "http://169.254.169.254/latest/meta-data",
    "http://[::1]/privacy", "https://user:pass@example.com/privacy",
    "https://example.com:8443/privacy", "http://2130706433/privacy",
])
def test_policy_url_rejects_unsafe_destinations(url):
    with pytest.raises(PolicyFetchError):
        normalize_policy_url(url)


def test_policy_url_removes_fragment_but_keeps_fetch_query():
    assert normalize_policy_url("https://example.com/privacy?lang=en#section") == "https://example.com/privacy?lang=en"


@pytest.mark.asyncio
async def test_resolver_rejects_private_dns_answer(monkeypatch):
    class FakeLoop:
        async def getaddrinfo(self, *args, **kwargs):
            return [(2, 1, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr("asyncio.get_running_loop", lambda: FakeLoop())
    with pytest.raises(PolicyFetchError, match="non-public"):
        await PublicResolver().resolve("public.example", 443)


@pytest.mark.asyncio
async def test_resolver_rejects_mixed_public_private_answers(monkeypatch):
    class FakeLoop:
        async def getaddrinfo(self, *args, **kwargs):
            return [
                (2, 1, 6, "", ("8.8.8.8", 443)),
                (10, 1, 6, "", ("::1", 443)),
            ]

    monkeypatch.setattr("asyncio.get_running_loop", lambda: FakeLoop())
    with pytest.raises(PolicyFetchError, match="non-public"):
        await PublicResolver().resolve("public.example", 443)


@pytest.mark.asyncio
async def test_existing_database_receives_versioned_migrations(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr("app.config.settings.sqlite_db_path", str(db_path))
    async with aiosqlite.connect(db_path) as db:
        await db.executescript("""
            CREATE TABLE sites (id TEXT PRIMARY KEY, domain TEXT UNIQUE NOT NULL);
            CREATE TABLE policies (id TEXT PRIMARY KEY, site_id TEXT NOT NULL, url TEXT NOT NULL,
                content_hash TEXT NOT NULL, retrieved_at TIMESTAMP, raw_text TEXT NOT NULL);
            CREATE TABLE policy_claims (id TEXT PRIMARY KEY, policy_id TEXT NOT NULL, category TEXT NOT NULL,
                data_type TEXT NOT NULL, purpose TEXT NOT NULL, sharing INTEGER NOT NULL, third_party TEXT,
                retention_specified INTEGER NOT NULL, retention_period TEXT, section_name TEXT NOT NULL,
                exact_quote TEXT NOT NULL, confidence REAL NOT NULL);
            CREATE TABLE scan_sessions (id TEXT PRIMARY KEY, site_id TEXT NOT NULL,
                started_at TIMESTAMP, status TEXT NOT NULL);
            CREATE TABLE observations (id TEXT PRIMARY KEY, site_id TEXT NOT NULL, timestamp INTEGER NOT NULL,
                target_domain TEXT NOT NULL, is_third_party INTEGER NOT NULL, category TEXT NOT NULL,
                initiator TEXT, method TEXT);
            CREATE TABLE findings (id TEXT PRIMARY KEY, site_id TEXT NOT NULL, gap_type TEXT NOT NULL,
                severity TEXT NOT NULL, confidence REAL NOT NULL, title TEXT NOT NULL, rationale TEXT NOT NULL,
                evidence_json TEXT NOT NULL);
            CREATE TABLE risk_snapshots (id TEXT PRIMARY KEY, site_id TEXT NOT NULL, timestamp TIMESTAMP,
                score INTEGER NOT NULL, tier TEXT NOT NULL, confidence REAL NOT NULL);
            """)
        await db.commit()
    await init_db()
    async with aiosqlite.connect(db_path) as db:
        versions = await (await db.execute("SELECT version FROM schema_migrations ORDER BY version")).fetchall()
        assert [row[0] for row in versions] == [1, 2, 3]
        columns = await (await db.execute("PRAGMA table_info(scan_sessions)")).fetchall()
        assert "policy_id" in {row[1] for row in columns}


@pytest.mark.asyncio
async def test_redirect_to_private_address_is_revalidated(monkeypatch):
    class Response:
        status = 302
        headers = {"Location": "http://127.0.0.1/privacy"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class Session:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("app.core.policy_fetcher.aiohttp.ClientSession", Session)
    with pytest.raises(PolicyFetchError, match="not public"):
        await fetch_public_policy("https://public.example/privacy")


@pytest.mark.asyncio
async def test_chunked_policy_response_cannot_exceed_limit(monkeypatch):
    class Content:
        async def iter_chunked(self, _size):
            yield b"x" * (MAX_POLICY_BYTES + 1)

    class Response:
        status = 200
        content_type = "text/html"
        content_length = None
        content = Content()
        charset = "utf-8"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class Session:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("app.core.policy_fetcher.aiohttp.ClientSession", Session)
    with pytest.raises(PolicyFetchError, match="size limit"):
        await fetch_public_policy("https://public.example/privacy")


@pytest.mark.asyncio
async def test_policy_fetch_timeout_is_sanitized(monkeypatch):
    class Session:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            raise asyncio.TimeoutError()

    monkeypatch.setattr("app.core.policy_fetcher.aiohttp.ClientSession", Session)
    with pytest.raises(PolicyFetchError, match="could not be reached safely"):
        await fetch_public_policy("https://public.example/privacy")
