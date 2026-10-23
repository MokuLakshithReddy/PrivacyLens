import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.config import settings


@pytest.mark.asyncio
async def test_delete_site_removes_related_records():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        domain = "delete-example.test"
        scan_id = "delete_scan_0001"
        await client.post("/api/v1/observations/ingest", json={
            "domain": domain,
            "scan_session_id": scan_id,
            "requests": [],
        })
        policy = await client.post("/api/v1/policies/analyze", json={
            "domain": domain,
            "policy_url": f"https://{domain}/privacy",
            "scan_session_id": scan_id,
            "policy_html": "<h1>Privacy</h1><p>We collect service logs.</p>",
        })
        assert policy.status_code == 200
        result = await client.post("/api/v1/correlate", json={
            "domain": domain,
            "scan_session_id": scan_id,
        })
        assert result.status_code == 200

        deleted = await client.delete(f"/api/v1/sites/{domain}")
        assert deleted.status_code == 200

    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        for table in ("sites", "scan_sessions", "observations", "policies", "policy_claims", "findings", "risk_snapshots"):
            cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
            assert (await cursor.fetchone())[0] == 0
