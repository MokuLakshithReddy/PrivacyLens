import uuid
from typing import List
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema
from app.schemas.correlation import EvidenceFindingSchema, FindingEvidenceSchema


class CorrelationEngine:
    """Conservative policy-to-observation rules; every result remains a candidate."""

    async def detect_privacy_gaps(
        self,
        domain: str,
        claims: List[PolicyClaimSchema],
        requests: List[NetworkSignalSchema],
        scan_session_id: str,
        policy_version_id: str,
        storage_keys: list | None = None,
        permissions: List[str] | None = None,
    ) -> List[EvidenceFindingSchema]:
        # A missing policy or empty extraction is insufficient evidence, not a gap.
        if not claims:
            return []

        ad_domains = sorted({
            request.targetDomain for request in requests
            if request.category == "advertising" and request.isThirdParty
        })
        disclosed = any(
            claim.purpose.lower() == "advertising"
            or "advertis" in claim.exact_quote.lower()
            or "marketing partner" in claim.exact_quote.lower()
            for claim in claims
        )
        if not ad_domains or disclosed:
            return []

        quotes = [claim.exact_quote for claim in claims[:2] if claim.exact_quote]
        rationale = (
            "Browser telemetry observed requests to domains classified by the current rule set as "
            f"advertising related ({', '.join(ad_domains[:5])}). The extracted claims from the captured "
            "policy did not contain an explicit advertising disclosure. This is a potential disclosure "
            "gap under heuristic rules; it does not establish what data was transmitted or a legal violation."
        )
        event_ids = sorted({
            request.requestId for request in requests
            if request.targetDomain in ad_domains and request.requestId
        })[:100]
        return [EvidenceFindingSchema(
            findingId=f"gap_ad_{uuid.uuid4().hex}",
            scanSessionId=scan_session_id,
            policyVersionId=policy_version_id,
            ruleId="third_party_advertising_disclosure",
            ruleVersion="rules-v1",
            gapType="omission_advertising",
            severity="high",
            title="Potential advertising disclosure gap",
            rationale=rationale,
            evidence=FindingEvidenceSchema(policyQuotes=quotes, observedDomains=ad_domains, observedEventIds=event_ids),
        )]
