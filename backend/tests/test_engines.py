import pytest
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema, StorageSignalSchema
from app.core.risk_engine import RiskEngine
from app.core.correlation_engine import CorrelationEngine
from app.core.policy_parser import clean_policy_html, segment_policy_sections

def test_clean_policy_html():
    raw_html = """
    <html>
        <head><title>Privacy</title><script>alert('noise')</script></head>
        <body>
            <header><nav><a href="/">Home</a></nav></header>
            <h1>Information We Collect</h1>
            <p>We collect device identifiers and email addresses for service operation.</p>
            <footer><p>Copyright 2026</p></footer>
        </body>
    </html>
    """
    cleaned = clean_policy_html(raw_html)
    assert "alert('noise')" not in cleaned
    assert "Copyright" not in cleaned
    assert "Information We Collect" in cleaned
    assert "We collect device identifiers" in cleaned

def test_deterministic_risk_engine():
    # Test low-risk scenario
    claims = [
        PolicyClaimSchema(
            claim_id="clm_1",
            category="data_collection",
            data_type="usage_metrics",
            purpose="analytics",
            sharing=False,
            retention_specified=True,
            section_name="Analytics",
            exact_quote="We collect anonymized telemetry.",
        )
    ]
    requests = [
        NetworkSignalSchema(
            url="https://example.com/api/ping",
            targetDomain="example.com",
            isThirdParty=False,
            category="essential"
        )
    ]
    findings = []

    score, tier, coverage, factors = RiskEngine.compute_risk(claims, requests, [], findings, True)
    assert score <= 30
    assert tier in ["Very Low", "Low"]
    assert 0.0 <= coverage <= 1.0
    assert "tracking" in factors

@pytest.mark.asyncio
async def test_gap_detection_omission_advertising():
    engine = CorrelationEngine()

    # Policy declares ONLY essential analytics
    claims = [
        PolicyClaimSchema(
            claim_id="clm_1",
            category="data_collection",
            data_type="analytics",
            purpose="service_uptime",
            sharing=False,
            retention_specified=False,
            section_name="General",
            exact_quote="We only collect system logs for uptime.",
        )
    ]

    # Browser observed advertising network
    requests = [
        NetworkSignalSchema(
            url="https://adservice.google.com/ads",
            targetDomain="adservice.google.com",
            isThirdParty=True,
            category="advertising"
        )
    ]

    findings = await engine.detect_privacy_gaps(
        domain="example.com",
        claims=claims,
        requests=requests,
        storage_keys=[],
        permissions=[],
        scan_session_id="scan_test_0001",
        policy_version_id="policy_test_0001",
    )

    assert len(findings) == 1
    assert findings[0].gapType == "omission_advertising"
    assert findings[0].severity == "high"
    assert "potential" in findings[0].title.lower()
    assert "adservice.google.com" in findings[0].evidence.observedDomains


@pytest.mark.asyncio
async def test_disclosure_matching_requires_domain_boundaries():
    engine = CorrelationEngine()
    claim = PolicyClaimSchema(
        claim_id="clm_google",
        category="sharing",
        data_type="identifiers",
        purpose="advertising",
        sharing=True,
        third_party="google.com",
        section_name="Advertising",
        exact_quote="We share identifiers with Google for advertising.",
    )
    request = NetworkSignalSchema(
        requestId="evt_google",
        url="https://notgoogle.com/pixel",
        targetDomain="notgoogle.com",
        isThirdParty=True,
        category="advertising",
    )
    findings = await engine.detect_privacy_gaps(
        domain="example.com",
        claims=[claim],
        requests=[request],
        scan_session_id="scan_boundary_0001",
        policy_version_id="policy_boundary_0001",
    )
    assert findings
    assert findings[0].evidence.observedDomains == ["notgoogle.com"]
