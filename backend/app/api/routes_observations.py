import hashlib
import uuid
from fastapi import APIRouter
import aiosqlite
from app.config import settings
from app.schemas.observation import ObservationIngestRequest, ObservationIngestResponse

router = APIRouter(prefix="/observations", tags=["Observations"])

@router.post("/ingest", response_model=ObservationIngestResponse)
async def ingest_observations(request: ObservationIngestRequest):
    """
    Ingests sanitized telemetry signals from the browser extension.
    THREAT MODEL: Strictly metadata only (domain names, categories, isThirdParty).
    """
    site_id = f"site_{hashlib.md5(request.domain.encode()).hexdigest()[:8]}"
    third_party_count = sum(1 for r in request.requests if r.isThirdParty)

    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        # Upsert site
        await db.execute(
            "INSERT OR IGNORE INTO sites (id, domain) VALUES (?, ?)",
            (site_id, request.domain)
        )
        await db.execute(
            "UPDATE sites SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
            (site_id,)
        )

        # Batch insert network observations
        for req in request.requests:
            obs_id = f"obs_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """INSERT INTO observations (
                    id, site_id, timestamp, target_domain, is_third_party, category, initiator, method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (obs_id, site_id, req.timestamp or 0, req.targetDomain, 1 if req.isThirdParty else 0,
                 req.category, req.initiator or "", req.method or "GET")
            )

        await db.commit()

    return ObservationIngestResponse(
        status="ingested",
        records_stored=len(request.requests) + len(request.storage_keys),
        third_party_count=third_party_count
    )
