import hashlib
import json
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
import aiosqlite
from app.config import settings
from app.ai.gemini_provider import GeminiAIProvider
from app.ai.mock_provider import MockAIProvider
from app.core.correlation_engine import CorrelationEngine
from app.core.risk_engine import RiskEngine
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema, StorageSignalSchema
from app.schemas.correlation import (
    CorrelateRequest,
    SiteAnalysisResultSchema,
    EvidenceFindingSchema,
    DataFlowSchema,
    ThirdPartyNodeSchema,
    TemporalChangeSchema
)

router = APIRouter(prefix="", tags=["Correlation & Sites"])

def get_ai_provider():
    if settings.default_ai_provider == "gemini":
        return GeminiAIProvider()
    return MockAIProvider()

@router.post("/correlate", response_model=SiteAnalysisResultSchema)
async def correlate_site(request: CorrelateRequest):
    """
    Main engine endpoint: Cross-evaluates declared policy claims against runtime observed signals.
    Computes deterministic risk score and detects Policy vs. Reality gaps.
    """
    domain = request.domain
    site_id = f"site_{hashlib.md5(domain.encode()).hexdigest()[:8]}"
    ai_provider = get_ai_provider()
    correlation_engine = CorrelationEngine(ai_provider)

    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row

        # 1. Fetch claims for domain
        cursor = await db.execute(
            """SELECT c.* FROM policy_claims c
               JOIN policies p ON c.policy_id = p.id
               WHERE p.site_id = ? ORDER BY p.retrieved_at DESC LIMIT 50""",
            (site_id,)
        )
        claims_rows = await cursor.fetchall()
        claims: List[PolicyClaimSchema] = [
            PolicyClaimSchema(
                claim_id=r["id"],
                category=r["category"],
                data_type=r["data_type"],
                purpose=r["purpose"],
                sharing=bool(r["sharing"]),
                third_party=r["third_party"],
                retention_specified=bool(r["retention_specified"]),
                retention_period=r["retention_period"],
                section_name=r["section_name"],
                exact_quote=r["exact_quote"],
                confidence=r["confidence"]
            )
            for r in claims_rows
        ]

        # 2. Fetch observations for domain
        cursor = await db.execute(
            """SELECT * FROM observations WHERE site_id = ? ORDER BY timestamp DESC LIMIT 60""",
            (site_id,)
        )
        obs_rows = await cursor.fetchall()
        requests: List[NetworkSignalSchema] = [
            NetworkSignalSchema(
                requestId=r["id"],
                url=r["target_domain"],
                targetDomain=r["target_domain"],
                initiator=r["initiator"],
                isThirdParty=bool(r["is_third_party"]),
                category=r["category"],
                method=r["method"] or "GET",
                timestamp=r["timestamp"]
            )
            for r in obs_rows
        ]

        # 3. Detect Privacy Gaps
        findings = await correlation_engine.detect_privacy_gaps(
            domain=domain,
            claims=claims,
            requests=requests,
            storage_keys=[],
            permissions=[]
        )

        # 4. Compute Deterministic Risk & Confidence
        risk_score, risk_tier, confidence = RiskEngine.compute_risk_and_confidence(
            claims=claims,
            requests=requests,
            storage_keys=[],
            findings=findings,
            policy_found=len(claims) > 0
        )

        # 5. Persist Findings & Risk Snapshot
        for f in findings:
            await db.execute(
                """INSERT OR REPLACE INTO findings (
                    id, site_id, gap_type, severity, confidence, title, rationale, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (f.findingId, site_id, f.gapType, f.severity, f.confidence, f.title,
                 f.rationale, f.evidence.model_dump_json())
            )

        snap_id = f"snp_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO risk_snapshots (id, site_id, score, tier, confidence) VALUES (?, ?, ?, ?, ?)",
            (snap_id, site_id, risk_score, risk_tier, confidence)
        )
        await db.commit()

        # 6. Build Data Flow Graph
        tp_domains = {}
        for req in requests:
            if req.isThirdParty:
                if req.targetDomain not in tp_domains:
                    tp_domains[req.targetDomain] = {
                        "category": req.category,
                        "count": 0,
                        "disclosed": any(
                            req.targetDomain in c.exact_quote.lower() or 
                            (c.third_party and c.third_party in req.targetDomain) 
                            for c in claims
                        )
                    }
                tp_domains[req.targetDomain]["count"] += 1

        third_parties_nodes = [
            ThirdPartyNodeSchema(
                domain=d,
                category=meta["category"],
                requestCount=meta["count"],
                disclosedInPolicy=meta["disclosed"]
            )
            for d, meta in tp_domains.items()
        ]

        # 7. Check Temporal History (Snapshot Diff)
        cursor = await db.execute(
            "SELECT score FROM risk_snapshots WHERE site_id = ? ORDER BY timestamp DESC LIMIT 2",
            (site_id,)
        )
        prev_snaps = await cursor.fetchall()
        temporal = None
        if len(prev_snaps) > 1:
            prev_score = prev_snaps[1]["score"]
            temporal = TemporalChangeSchema(
                previousScore=prev_score,
                scoreDelta=risk_score - prev_score
            )

    return SiteAnalysisResultSchema(
        domain=domain,
        policyUrl=request.policy_url,
        inspectedAt=datetime.utcnow().isoformat(),
        riskScore=risk_score,
        riskTier=risk_tier,
        confidence=confidence,
        summary=f"Automated evaluation completed with {len(findings)} detected gap candidates across {len(requests)} observable signals.",
        claimsCount=len(claims),
        observedThirdPartiesCount=len(third_parties_nodes),
        findings=findings,
        dataFlow=DataFlowSchema(
            firstParty=domain,
            thirdParties=third_parties_nodes
        ),
        temporalChange=temporal
    )

@router.get("/sites/{domain}/diff")
async def get_site_temporal_diff(domain: str):
    """
    Returns temporal risk score evolution and policy changes for the domain.
    """
    site_id = f"site_{hashlib.md5(domain.encode()).hexdigest()[:8]}"
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT score, tier, confidence, timestamp FROM risk_snapshots WHERE site_id = ? ORDER BY timestamp DESC LIMIT 10",
            (site_id,)
        )
        rows = await cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No historical records for site")

        return {
            "domain": domain,
            "snapshots": [dict(r) for r in rows]
        }
