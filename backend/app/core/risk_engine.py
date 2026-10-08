from typing import List, Tuple
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema, StorageSignalSchema
from app.schemas.correlation import EvidenceFindingSchema

class RiskEngine:
    """
    Deterministic Risk & Confidence Engine.
    Computes mathematical risk (0-100) and evidentiary confidence (0.0 - 1.0)
    independently of LLM completion randomness.
    """

    @staticmethod
    def compute_risk_and_confidence(
        claims: List[PolicyClaimSchema],
        requests: List[NetworkSignalSchema],
        storage_keys: List[StorageSignalSchema],
        findings: List[EvidenceFindingSchema],
        policy_found: bool = True
    ) -> Tuple[int, str, float]:
        # --- 1. S_collection (0 - 100, weight 0.15) ---
        sensitive_keywords = ["biometric", "location", "financial", "health", "children"]
        sensitive_count = sum(
            1 for c in claims 
            if any(k in c.data_type.lower() or k in c.exact_quote.lower() for k in sensitive_keywords)
        )
        s_collection = min(100, sensitive_count * 25 + (20 if len(claims) > 0 else 0))

        # --- 2. S_sharing (0 - 100, weight 0.20) ---
        sharing_claims = [c for c in claims if c.sharing or c.purpose == "advertising"]
        s_sharing = min(100, len(sharing_claims) * 30)

        # --- 3. S_retention (0 - 100, weight 0.10) ---
        has_retention_limit = any(c.retention_specified for c in claims)
        s_retention = 20 if has_retention_limit else 75

        # --- 4. S_observed_tracking (0 - 100, weight 0.25) ---
        third_parties = [r for r in requests if r.isThirdParty]
        ad_count = sum(1 for r in third_parties if r.category == "advertising")
        analytics_count = sum(1 for r in third_parties if r.category == "analytics")
        unique_tp_domains = len(set(r.targetDomain for r in third_parties))

        s_tracking = min(100, (unique_tp_domains * 12) + (ad_count * 15) + (analytics_count * 8))

        # --- 5. S_policy_gap (0 - 100, weight 0.25) ---
        gap_penalty = 0
        for f in findings:
            if f.severity == "critical": gap_penalty += 40
            elif f.severity == "high": gap_penalty += 30
            elif f.severity == "medium": gap_penalty += 18
            else: gap_penalty += 8
        s_gap = min(100, gap_penalty)

        # --- 6. S_transparency (0 - 100, weight 0.05) ---
        s_transparency = 30 if policy_found else 80

        # Weighted Sum
        raw_risk = (
            s_collection * 0.15 +
            s_sharing * 0.20 +
            s_retention * 0.10 +
            s_tracking * 0.25 +
            s_gap * 0.25 +
            s_transparency * 0.05
        )
        final_risk = int(round(min(100, max(0, raw_risk))))

        # Tier classification
        if final_risk <= 20: tier = "Very Low"
        elif final_risk <= 40: tier = "Low"
        elif final_risk <= 60: tier = "Moderate"
        elif final_risk <= 80: tier = "High"
        else: tier = "Critical"

        # --- Evidentiary Confidence Calculation ---
        # C_policy: 1.0 if parsed with claims, 0.4 if partial, 0.1 if missing
        c_policy = 1.0 if len(claims) >= 3 else (0.5 if policy_found else 0.1)

        # C_telemetry: scales with observation volume (saturated at >= 10 requests)
        c_telemetry = min(1.0, max(0.2, len(requests) / 10.0))

        # C_correlation: high if findings are grounded in verified domains
        c_correlation = 0.9 if findings else 0.75

        confidence = round(c_policy * 0.40 + c_telemetry * 0.35 + c_correlation * 0.25, 2)
        confidence = min(0.99, max(0.10, confidence))

        return final_risk, tier, confidence
