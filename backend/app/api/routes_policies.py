import asyncio
import hashlib
import uuid

import aiosqlite
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.db.database import database_connection
from app.core.domain_identity import site_id_for_domain
from app.core.policy_fetcher import PolicyFetchError, fetch_public_policy, normalize_policy_url, storage_safe_url
from app.core.policy_parser import clean_policy_html, segment_policy_sections
from app.core.claim_extractor import ClaimExtractor
from app.schemas.policy import (
    PolicyDiscoverRequest,
    PolicyDiscoverResponse,
    PolicyAnalyzeRequest,
    PolicyAnalyzeResponse,
)

router = APIRouter(prefix="/policies", tags=["Policies"])
claim_extractor = ClaimExtractor()
MAX_POLICY_HTML_CHARS = 1_000_000


@router.post("/discover", response_model=PolicyDiscoverResponse)
async def discover_policy(request: PolicyDiscoverRequest):
    """Probe standard policy paths using the SSRF-safe bounded fetcher."""
    try:
        base = normalize_policy_url(request.url).rstrip("/")
    except PolicyFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    candidates = [
        f"{base}/privacy", f"{base}/privacy-policy", f"{base}/privacy.html",
        f"{base}/.well-known/privacy-policy",
    ]
    try:
        async with asyncio.timeout(15):
            return await _discover_candidates(candidates)
    except TimeoutError:
        pass

    return PolicyDiscoverResponse(
        discovered=False, policy_url=None, source="discovery_fallback"
    )


async def _discover_candidates(candidates: list[str]) -> PolicyDiscoverResponse:
    for candidate in candidates:
        try:
            fetched = await fetch_public_policy(candidate)
            if fetched.text.strip():
                return PolicyDiscoverResponse(
                    discovered=True,
                    policy_url=storage_safe_url(fetched.final_url),
                    source="well_known_path",
                )
        except PolicyFetchError:
            continue

    return PolicyDiscoverResponse(
        discovered=False, policy_url=None, source="discovery_fallback"
    )


@router.post("/analyze", response_model=PolicyAnalyzeResponse)
async def analyze_policy(request: PolicyAnalyzeRequest):
    """Analyze supplied policy text or fetch it through the public-policy boundary."""
    try:
        safe_source_url = storage_safe_url(request.policy_url)
    except PolicyFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    html_content = request.policy_html
    if html_content is None:
        try:
            fetched = await fetch_public_policy(request.policy_url)
            html_content = fetched.text
            safe_source_url = storage_safe_url(fetched.final_url)
        except PolicyFetchError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if len(html_content) > MAX_POLICY_HTML_CHARS:
        raise HTTPException(status_code=413, detail="Policy content exceeds the size limit")

    clean_text = clean_policy_html(html_content)
    content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    sections = segment_policy_sections(html_content)
    site_id = site_id_for_domain(request.domain.lower().rstrip("."))

    async with database_connection() as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT OR IGNORE INTO sites (id, domain) VALUES (?, ?)",
            (site_id, request.domain.lower().rstrip(".")),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id FROM policies WHERE site_id = ? AND content_hash = ? ORDER BY retrieved_at DESC LIMIT 1",
            (site_id, content_hash),
        )
        existing = await cursor.fetchone()
        if existing:
            cursor = await db.execute("SELECT * FROM policy_claims WHERE policy_id = ? LIMIT 50", (existing["id"],))
            existing_claims = [PolicyClaimSchema(
                claim_id=row["id"], category=row["category"], data_type=row["data_type"],
                purpose=row["purpose"], sharing=bool(row["sharing"]), third_party=row["third_party"],
                retention_specified=bool(row["retention_specified"]), retention_period=row["retention_period"],
                section_name=row["section_name"], exact_quote=row["exact_quote"],
            ) for row in await cursor.fetchall()]
            return PolicyAnalyzeResponse(
                policy_id=existing["id"], domain=request.domain,
                analysis_method=claim_extractor.analysis_method, claims_count=len(existing_claims),
                sections=[section["section_name"] for section in sections], claims=existing_claims,
            )

    try:
        claims = await asyncio.wait_for(claim_extractor.process_sections(sections[:30]), timeout=45)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Policy analysis timed out") from exc

    policy_id = f"pol_{uuid.uuid4().hex}"
    async with database_connection() as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "INSERT INTO policies (id, site_id, url, content_hash, raw_text) VALUES (?, ?, ?, ?, ?)",
            (policy_id, site_id, safe_source_url, content_hash, clean_text[:50000]),
        )
        for claim in claims:
            await db.execute(
                """INSERT INTO policy_claims (
                    id, policy_id, category, data_type, purpose, sharing, third_party,
                    retention_specified, retention_period, section_name, exact_quote, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (claim.claim_id, policy_id, claim.category, claim.data_type, claim.purpose,
                 int(claim.sharing), claim.third_party, int(claim.retention_specified),
                 claim.retention_period, claim.section_name, claim.exact_quote, 0.0),
            )
        await db.commit()

    return PolicyAnalyzeResponse(
        policy_id=policy_id,
        domain=request.domain,
        analysis_method=claim_extractor.analysis_method,
        claims_count=len(claims),
        sections=[section["section_name"] for section in sections],
        claims=claims,
    )
