import time
import uuid

from fastapi import APIRouter
from app.config import settings
from app.db.database import database_connection
from app.core.domain_identity import site_id_for_domain
from app.schemas.observation import ObservationIngestRequest, ObservationIngestResponse

router = APIRouter(prefix="/observations", tags=["Observations"])


@router.post("/ingest", response_model=ObservationIngestResponse)
async def ingest_observations(request: ObservationIngestRequest):
    """Persist bounded network metadata for one scan session. Storage and permission
    fields are deliberately unsupported and never accepted or reported as stored.
    """
    domain = request.domain.lower().rstrip(".")
    site_id = site_id_for_domain(domain)
    stored = 0
    third_party_stored = 0

    async with database_connection() as db:
        await db.execute("INSERT OR IGNORE INTO sites (id, domain) VALUES (?, ?)", (site_id, domain))
        await db.execute("UPDATE sites SET last_seen = CURRENT_TIMESTAMP WHERE id = ?", (site_id,))
        await db.execute(
            "INSERT OR IGNORE INTO scan_sessions (id, site_id) VALUES (?, ?)",
            (request.scan_session_id, site_id),
        )
        for signal in request.requests:
            event_id = signal.requestId or uuid.uuid4().hex
            await db.execute(
                """INSERT OR IGNORE INTO observations (
                    id, site_id, scan_session_id, event_id, timestamp, target_domain,
                    is_third_party, category, initiator, method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"obs_{uuid.uuid4().hex}", site_id, request.scan_session_id, event_id,
                 signal.timestamp if signal.timestamp is not None else int(time.time() * 1000),
                 signal.targetDomain, int(signal.isThirdParty), signal.category,
                 signal.initiator or "", signal.method),
            )
            cursor = await db.execute("SELECT changes()")
            inserted = (await cursor.fetchone())[0] > 0
            if inserted:
                stored += 1
                third_party_stored += int(signal.isThirdParty)
        await db.commit()

    return ObservationIngestResponse(
        status="ingested",
        records_stored=stored,
        third_party_count=third_party_stored,
        unsupported_categories=["storage", "permissions"],
    )
