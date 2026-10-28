import hashlib
import time
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
    THREAT MODEL: Strictly metadata only (domain names, categories, isThirdParty, storage keys, permissions).
    Zero values or PII collected.
    """
    site_id = f"site_{hashlib.md5(request.domain.encode()).hexdigest()[:8]}"
    third_party_count = sum(1 for r in request.requests if r.isThirdParty)
    now_ts = int(time.time())

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
                (obs_id, site_id, req.timestamp or now_ts, req.targetDomain, 1 if req.isThirdParty else 0,
                 req.category, req.initiator or "", req.method or "GET")
            )

        # Batch insert storage observations
        for st in request.storage_keys:
            st_id = f"sto_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """INSERT INTO storage_observations (
                    id, site_id, type, name, is_third_party, persistent, byte_length, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (st_id, site_id, st.type, st.name, 1 if st.isThirdParty else 0,
                 1 if st.persistent else 0, st.byteLength or 0, now_ts)
            )

        # Batch insert permission observations
        for perm in request.permissions:
            perm_id = f"prm_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """INSERT INTO permission_observations (
                    id, site_id, permission, state, timestamp
                ) VALUES (?, ?, ?, ?, ?)""",
                (perm_id, site_id, perm, "queried", now_ts)
            )

        await db.commit()

    total_records = len(request.requests) + len(request.storage_keys) + len(request.permissions)
    return ObservationIngestResponse(
        status="ingested",
        records_stored=total_records,
        third_party_count=third_party_count
    )
