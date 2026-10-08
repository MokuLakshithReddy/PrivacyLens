import uuid
from typing import List, Dict, Any
from app.ai.base import BaseAIProvider
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema, StorageSignalSchema
from app.schemas.correlation import EvidenceFindingSchema, FindingEvidenceSchema

class CorrelationEngine:
    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider

    async def detect_privacy_gaps(
        self,
        domain: str,
        claims: List[PolicyClaimSchema],
        requests: List[NetworkSignalSchema],
        storage_keys: List[StorageSignalSchema],
        permissions: List[str]
    ) -> List[EvidenceFindingSchema]:
        findings: List[EvidenceFindingSchema] = []

        # 1. Inspect Advertising Network Discrepancies
        ad_requests = [r for r in requests if r.category == "advertising" and r.isThirdParty]
        ad_domains = list(set([r.targetDomain for r in ad_requests]))
        
        has_ad_disclosure = any(
            c.purpose == "advertising" or (c.sharing and "ad" in (c.third_party or "").lower())
            for c in claims
        )

        if ad_domains and not has_ad_disclosure:
            rationale = await self.ai_provider.generate_finding_rationale(
                gap_type="omission_advertising",
                policy_quotes=[c.exact_quote for c in claims if "collect" in c.category.lower()][:2],
                observed_signals=[{"targetDomain": d, "category": "advertising"} for d in ad_domains]
            )
            findings.append(EvidenceFindingSchema(
                findingId=f"gap_ad_{uuid.uuid4().hex[:6]}",
                gapType="omission_advertising",
                severity="high",
                confidence=0.92,
                title="Undisclosed Third-Party Advertising Network",
                rationale=rationale,
                evidence=FindingEvidenceSchema(
                    policyQuotes=[c.exact_quote for c in claims if c.category == "data_collection"][:1],
                    observedDomains=ad_domains,
                    observedStorageKeys=[s.name for s in storage_keys if any(k in s.name for k in ["_fbp", "_gcl", "IDE"])]
                )
            ))

        # 2. Inspect Permission Discrepancies (e.g. Geolocation)
        if "geolocation" in permissions:
            has_location_disclosure = any(
                "location" in c.data_type.lower() or "location" in c.exact_quote.lower()
                for c in claims
            )
            if not has_location_disclosure:
                rationale = await self.ai_provider.generate_finding_rationale(
                    gap_type="permission_mismatch",
                    policy_quotes=[],
                    observed_signals=[{"permission": "geolocation", "domain": domain}]
                )
                findings.append(EvidenceFindingSchema(
                    findingId=f"gap_geo_{uuid.uuid4().hex[:6]}",
                    gapType="permission_mismatch",
                    severity="medium",
                    confidence=0.84,
                    title="Location Capability Query Without Specific Disclosure",
                    rationale=rationale,
                    evidence=FindingEvidenceSchema(
                        policyQuotes=[],
                        observedDomains=[domain],
                        observedPermissions=["geolocation"]
                    )
                ))

        # 3. Inspect Broad Language vs Ecosystem Density
        third_party_domains = list(set([r.targetDomain for r in requests if r.isThirdParty]))
        generic_claims = [
            c for c in claims 
            if any(term in c.exact_quote.lower() for term in ["service improvement", "business partners", "legitimate interests", "as necessary"])
        ]
        
        if len(third_party_domains) >= 4 and generic_claims:
            rationale = await self.ai_provider.generate_finding_rationale(
                gap_type="broad_language_concern",
                policy_quotes=[c.exact_quote for c in generic_claims[:2]],
                observed_signals=[{"targetDomain": d} for d in third_party_domains[:4]]
            )
            findings.append(EvidenceFindingSchema(
                findingId=f"gap_broad_{uuid.uuid4().hex[:6]}",
                gapType="broad_language_concern",
                severity="medium",
                confidence=0.80,
                title="Expansive Policy Terminology Relative to Active Emitters",
                rationale=rationale,
                evidence=FindingEvidenceSchema(
                    policyQuotes=[generic_claims[0].exact_quote],
                    observedDomains=third_party_domains[:5]
                )
            ))

        # 4. Retention & Deletion Disclosure
        has_retention = any(c.retention_specified for c in claims)
        persistent_storage = [s for s in storage_keys if s.persistent]
        if persistent_storage and not has_retention:
            findings.append(EvidenceFindingSchema(
                findingId=f"gap_ret_{uuid.uuid4().hex[:6]}",
                gapType="excessive_persistence",
                severity="low",
                confidence=0.76,
                title="Persistent Browser State Without Explicit Retention Limits",
                rationale="Persistent storage identifiers detected, but no explicit data retention duration or expiration policy was identified in the published terms.",
                evidence=FindingEvidenceSchema(
                    policyQuotes=[],
                    observedDomains=[domain],
                    observedStorageKeys=[s.name for s in persistent_storage[:5]]
                )
            ))

        return findings
