import pytest
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema, StorageSignalSchema
from app.core.risk_engine import RiskEngine
from app.core.correlation_engine import CorrelationEngine
from app.ai.mock_provider import MockAIProvider
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
            confidence=0.9
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

    score, tier, conf = RiskEngine.compute_risk_and_confidence(claims, requests, [], findings, True)
    assert score <= 30
    assert tier in ["Very Low", "Low"]
    assert 0.0 < conf <= 1.0

@pytest.mark.asyncio
async def test_gap_detection_omission_advertising():
    mock_ai = MockAIProvider()
    engine = CorrelationEngine(mock_ai)

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
            confidence=0.95
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
        permissions=[]
    )

    assert len(findings) == 1
    assert findings[0].gapType == "omission_advertising"
    assert findings[0].severity == "high"
    assert "adservice.google.com" in findings[0].evidence.observedDomains
