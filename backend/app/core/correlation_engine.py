import uuid
import re
from typing import List
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema
from app.schemas.correlation import EvidenceFindingSchema, FindingEvidenceSchema


def _canonical_domain(value: str) -> str | None:
    candidate = value.strip().lower().rstrip(".")
    if "://" in candidate:
        candidate = candidate.split("://", 1)[1].split("/", 1)[0]
    candidate = candidate.split(":", 1)[0].removeprefix("www.")
    if "." not in candidate or not re.fullmatch(r"[a-z0-9.-]+", candidate):
        return None
    return candidate


def _domain_matches(named_party: str, observed_domain: str) -> bool:
    named_domain = _canonical_domain(named_party)
    observed = _canonical_domain(observed_domain)
    if named_domain and observed:
        return observed == named_domain or observed.endswith(f".{named_domain}")

    organization = re.sub(r"[^a-z0-9]", "", named_party.lower())
    observed_parts = (observed or observed_domain.lower()).split(".")
    observed_organization = re.sub(r"[^a-z0-9]", "", observed_parts[-2] if len(observed_parts) > 1 else observed_parts[0])
    return bool(organization) and organization == observed_organization


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
                    _domain_matches(claim.third_party, domain)
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
