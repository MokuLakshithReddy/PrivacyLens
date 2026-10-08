import json
from fastapi import APIRouter, HTTPException
import aiosqlite
from app.config import settings

router = APIRouter(prefix="/evidence", tags=["Evidence Audit"])

@router.get("/findings/{finding_id}")
async def get_finding_evidence(finding_id: str):
    """
    Dedicated Evidence Audit API: Returns complete evidentiary backing for any detected finding.
    """
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM findings WHERE id = ?",
            (finding_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")

        finding_dict = dict(row)
        finding_dict["evidence"] = json.loads(finding_dict["evidence_json"])
        del finding_dict["evidence_json"]
        return finding_dict
