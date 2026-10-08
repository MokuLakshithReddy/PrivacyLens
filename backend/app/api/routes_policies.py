import hashlib
import uuid
import httpx
from fastapi import APIRouter, HTTPException
import aiosqlite
from app.config import settings
from app.core.policy_parser import clean_policy_html, segment_policy_sections
from app.core.claim_extractor import ClaimExtractor
from app.schemas.policy import (
    PolicyDiscoverRequest,
    PolicyDiscoverResponse,
    PolicyAnalyzeRequest,
    PolicyAnalyzeResponse,
    PolicyClaimSchema
)

router = APIRouter(prefix="/policies", tags=["Policies"])
claim_extractor = ClaimExtractor()

@router.post("/discover", response_model=PolicyDiscoverResponse)
async def discover_policy(request: PolicyDiscoverRequest):
    """
    Attempts to discover candidate privacy policy links from target URL or standard well-known paths.
    """
    url = request.url.rstrip("/")
    candidates = [
        f"{url}/privacy",
        f"{url}/privacy-policy",
        f"{url}/privacy.html",
        f"{url}/.well-known/privacy-policy"
    ]

    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
        for candidate in candidates:
            try:
                res = await client.head(candidate)
                if res.status_code == 200:
                    return PolicyDiscoverResponse(
                        discovered=True,
                        policy_url=candidate,
                        source="well_known_path",
                        confidence=0.92
                    )
            except Exception:
                continue

    return PolicyDiscoverResponse(
        discovered=False,
        policy_url=None,
        source="discovery_fallback",
        confidence=0.0
    )

@router.post("/analyze", response_model=PolicyAnalyzeResponse)
async def analyze_policy(request: PolicyAnalyzeRequest):
    """
    Cleans, segments, and extracts structured claims from policy HTML or fetched policy URL.
    """
    html_content = request.policy_html

    # Fetch policy content if not supplied directly
    if not html_content:
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(request.policy_url)
                if res.status_code == 200:
                    html_content = res.text
                else:
                    raise HTTPException(status_code=400, detail="Could not fetch policy URL")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed retrieving policy URL: {str(e)}")

    clean_text = clean_policy_html(html_content)
    sections = segment_policy_sections(html_content)
    claims = await claim_extractor.process_sections(sections)

    content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"

    # Persist in SQLite
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        # Upsert site
        site_id = f"site_{hashlib.md5(request.domain.encode()).hexdigest()[:8]}"
        await db.execute(
            "INSERT OR IGNORE INTO sites (id, domain) VALUES (?, ?)",
            (site_id, request.domain)
        )
        # Insert policy
        await db.execute(
            "INSERT INTO policies (id, site_id, url, content_hash, raw_text) VALUES (?, ?, ?, ?, ?)",
            (policy_id, site_id, request.policy_url, content_hash, clean_text[:50000])
        )
        # Insert claims
        for c in claims:
            await db.execute(
                """INSERT INTO policy_claims (
                    id, policy_id, category, data_type, purpose, sharing, third_party,
                    retention_specified, retention_period, section_name, exact_quote, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (c.claim_id, policy_id, c.category, c.data_type, c.purpose, 1 if c.sharing else 0,
                 c.third_party, 1 if c.retention_specified else 0, c.retention_period,
                 c.section_name, c.exact_quote, c.confidence)
            )
        await db.commit()

    return PolicyAnalyzeResponse(
        policy_id=policy_id,
        domain=request.domain,
        claims_count=len(claims),
        sections=[s["section_name"] for s in sections],
        claims=claims
    )
