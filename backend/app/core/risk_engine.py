from typing import List, Tuple
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema, StorageSignalSchema
from app.schemas.correlation import EvidenceFindingSchema


class RiskEngine:
    """Deterministic heuristic risk indicator with visible score factors.

    The output is not a legal compliance score or a calibrated probability.
    """

    WEIGHTS = {
        "collection": 0.15,
        "sharing": 0.20,
        "retention": 0.10,
        "tracking": 0.25,
        "gap_candidates": 0.25,
        "transparency": 0.05,
    }

    @staticmethod
    def compute_risk(
        claims: List[PolicyClaimSchema],
        requests: List[NetworkSignalSchema],
        storage_keys: List[StorageSignalSchema],
        findings: List[EvidenceFindingSchema],
        policy_found: bool = True,
    ) -> Tuple[int, str, float, dict[str, int]]:
        sensitive_terms = ("biometric", "location", "financial", "health", "children")
        sensitive_count = sum(
            any(term in claim.data_type.lower() or term in claim.exact_quote.lower() for term in sensitive_terms)
            for claim in claims
        )
        factors = {
            "collection": min(100, sensitive_count * 25 + (20 if claims else 0)),
            "sharing": min(100, sum(claim.sharing or claim.purpose == "advertising" for claim in claims) * 30),
            "retention": 20 if any(claim.retention_specified for claim in claims) else 75,
        }
        unique_requests = {(r.targetDomain, r.category, r.isThirdParty) for r in requests}
        third_party_domains = {domain for domain, _category, third_party in unique_requests if third_party}
        ad_domains = {domain for domain, category, third_party in unique_requests if third_party and category == "advertising"}
        analytics_domains = {domain for domain, category, third_party in unique_requests if third_party and category == "analytics"}
        factors["tracking"] = min(100, len(third_party_domains) * 12 + len(ad_domains) * 15 + len(analytics_domains) * 8)
        gap_penalty = sum({"critical": 40, "high": 30, "medium": 18}.get(f.severity, 8) for f in findings)
        factors["gap_candidates"] = min(100, gap_penalty)
        factors["transparency"] = 30 if policy_found else 80

        weighted = sum(factors[name] * weight for name, weight in RiskEngine.WEIGHTS.items())
        score = int(round(min(100, max(0, weighted))))
        tier = "Very Low" if score <= 20 else "Low" if score <= 40 else "Moderate" if score <= 60 else "High" if score <= 80 else "Critical"

        # This estimate describes the presence of input categories, not finding correctness.
        policy_input = 1.0 if policy_found and claims else 0.5 if policy_found else 0.0
        telemetry_input = min(1.0, len(unique_requests) / 15.0)
        classified = {"advertising", "analytics", "social", "cdn", "essential", "telemetry"}
        domains = {r.targetDomain for r in requests}
        known_domains = {r.targetDomain for r in requests if r.category in classified}
        correlation_input = len(known_domains) / len(domains) if domains else 0.0
        coverage = round(policy_input * 0.40 + telemetry_input * 0.35 + correlation_input * 0.25, 2)
        return score, tier, coverage, factors
