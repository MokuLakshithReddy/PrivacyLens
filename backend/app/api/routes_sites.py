import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException
import aiosqlite
from app.config import settings
from app.db.database import database_connection
from app.core.domain_identity import site_id_for_domain
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

@router.post("/correlate", response_model=SiteAnalysisResultSchema)
async def correlate_site(request: CorrelateRequest):
    """
    Main engine endpoint: Cross-evaluates declared policy claims against runtime observed signals.
    Computes deterministic risk score and detects Policy vs. Reality gaps.
    """
    domain = request.domain
    site_id = site_id_for_domain(domain)
    correlation_engine = CorrelationEngine()

    async with database_connection() as db:
        db.row_factory = aiosqlite.Row

        # A scan can only use the newest policy version available for this site.
        cursor = await db.execute(
            "SELECT id FROM scan_sessions WHERE id = ? AND site_id = ?",
            (request.scan_session_id, site_id),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Scan session not found for this site")

        cursor = await db.execute(
            "SELECT id FROM policies WHERE site_id = ? ORDER BY retrieved_at DESC LIMIT 1",
            (site_id,),
        )
        policy_row = await cursor.fetchone()
        policy_id = policy_row["id"] if policy_row else None

        # 1. Fetch claims for this exact policy version.
        cursor = await db.execute(
            "SELECT * FROM policy_claims WHERE policy_id = ? LIMIT 50",
            (policy_id,),
        ) if policy_id else None
        claims_rows = await cursor.fetchall() if cursor else []
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
            )
            for r in claims_rows
        ]

        # 2. Fetch observations for domain
        cursor = await db.execute(
            """SELECT * FROM observations WHERE site_id = ? AND scan_session_id = ?
               ORDER BY timestamp DESC LIMIT 200""",
            (site_id, request.scan_session_id)
        )
        obs_rows = await cursor.fetchall()
        requests: List[NetworkSignalSchema] = [
            NetworkSignalSchema(
                requestId=r["event_id"] or r["id"],
                url=f"https://{r['target_domain']}",
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
            permissions=[],
            scan_session_id=request.scan_session_id,
            policy_version_id=policy_id,
        )

        # 4. Compute deterministic risk indicators and input coverage estimate
        risk_score, risk_tier, evidence_coverage, risk_factors = RiskEngine.compute_risk(
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
                    id, site_id, scan_session_id, policy_id, rule_version, gap_type,
                    severity, confidence, title, rationale, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f.findingId, site_id, request.scan_session_id, policy_id, "rules-v1",
                 f.gapType, f.severity, 0.0, f.title, f.rationale,
                 f.evidence.model_dump_json())
            )

        snap_id = f"snp_{uuid.uuid4().hex[:8]}"
        await db.execute(
            """INSERT INTO risk_snapshots (
                id, site_id, scan_session_id, algorithm_version, input_summary, score, tier, confidence, evidence_coverage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (snap_id, site_id, request.scan_session_id, "risk-v2",
             json.dumps({"claims": len(claims), "observations": len(requests), "findings": len(findings)}),
             risk_score, risk_tier, 0.0, evidence_coverage)
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
        policyUrl=(request.policy_url.split("?", 1)[0].split("#", 1)[0] if request.policy_url else None),
        inspectedAt=datetime.now(timezone.utc).isoformat(),
        riskScore=risk_score,
        riskTier=risk_tier,
        evidenceCoverage=evidence_coverage,
        riskFactors=risk_factors,
        riskWeights=RiskEngine.WEIGHTS,
        algorithmVersion="risk-v2",
        summary=(f"Heuristic risk indicators were calculated from {len(claims)} policy claims and "
                 f"{len(requests)} observations in this scan. No finding is not a safety or compliance assessment."),
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
    site_id = site_id_for_domain(domain)
    async with database_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT score, tier, evidence_coverage, timestamp FROM risk_snapshots WHERE site_id = ? ORDER BY timestamp DESC LIMIT 10",
            (site_id,)
        )
        rows = await cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No historical records for site")

        return {
            "domain": domain,
            "snapshots": [dict(r) for r in rows]
        }
