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
        if not ad_domains:
            return []

        relevant_claims = [
            claim for claim in claims
            if any(term in " ".join((claim.category, claim.purpose, claim.data_type, claim.exact_quote)).lower()
                   for term in ("advertis", "marketing", "targeted", "promotion"))
        ]
        named_matches = {
            domain for domain in ad_domains
            if any(
                claim.third_party and (
                    claim.third_party.lower() in domain.lower()
                    or domain.lower() in claim.third_party.lower()
                )
                for claim in relevant_claims
            )
        }
        if named_matches == set(ad_domains):
            return []

        unmatched_domains = [domain for domain in ad_domains if domain not in named_matches]
        quotes = [claim.exact_quote for claim in relevant_claims if claim.exact_quote][:2]
        locations = [
            {"start": claim.source_start, "end": claim.source_end}
            for claim in relevant_claims[:2]
            if claim.source_start is not None and claim.source_end is not None
        ]
        disclosure_status = "ambiguous_disclosure" if relevant_claims else "potential_disclosure_gap"
        rationale = (
            "Browser telemetry observed requests to domains classified by the current rule set as "
            f"advertising related ({', '.join(unmatched_domains[:5])}). The relevant extracted claims "
            "did not name every observed destination. This is a candidate disclosure "
            "gap under heuristic rules; it does not establish what data was transmitted or a legal violation."
        )
        event_ids = sorted({
            request.requestId for request in requests
            if request.targetDomain in unmatched_domains and request.requestId
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
            evidence=FindingEvidenceSchema(
                policyQuotes=quotes,
                policyLocations=locations,
                disclosureStatus=disclosure_status,
                observedDomains=unmatched_domains,
                observedEventIds=event_ids,
            ),
        )]
