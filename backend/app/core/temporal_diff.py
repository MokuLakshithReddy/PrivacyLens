from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.policy import PolicyClaimSchema
from app.schemas.observation import NetworkSignalSchema

class ClaimDelta(BaseModel):
    category: str
    data_type: str
    purpose: str
    change_type: str # "added", "removed", "scope_expanded"
    description: str
    exact_quote: str

class TelemetryDelta(BaseModel):
    new_third_party_domains: List[str]
    removed_third_party_domains: List[str]
    category_shifts: Dict[str, int]
    net_tracker_count_delta: int

class TemporalPostureComparison(BaseModel):
    domain: str
    previous_score: Optional[int]
    current_score: int
    score_delta: int
    posture_direction: str # "improved", "degraded", "stable"
    claim_deltas: List[ClaimDelta]
    telemetry_delta: TelemetryDelta
    summary: str

class TemporalDiffEngine:
    """
    Computes semantic policy changes and runtime telemetry drift across time.
    """

    @staticmethod
    def compute_claim_diff(
        prev_claims: List[PolicyClaimSchema],
        curr_claims: List[PolicyClaimSchema]
    ) -> List[ClaimDelta]:
        deltas: List[ClaimDelta] = []
        prev_keys = {(c.category, c.data_type, c.purpose): c for c in prev_claims}
        curr_keys = {(c.category, c.data_type, c.purpose): c for c in curr_claims}

        # Added claims
        for key, curr_c in curr_keys.items():
            if key not in prev_keys:
                is_expansion = curr_c.sharing or curr_c.purpose in ("advertising", "data_sale")
                deltas.append(ClaimDelta(
                    category=curr_c.category,
                    data_type=curr_c.data_type,
                    purpose=curr_c.purpose,
                    change_type="scope_expanded" if is_expansion else "added",
                    description=f"New disclosure: {curr_c.category} collection for {curr_c.purpose}",
                    exact_quote=curr_c.exact_quote
                ))

        # Removed claims
        for key, prev_c in prev_keys.items():
            if key not in curr_keys:
                deltas.append(ClaimDelta(
                    category=prev_c.category,
                    data_type=prev_c.data_type,
                    purpose=prev_c.purpose,
                    change_type="removed",
                    description=f"Removed disclosure: {prev_c.category} ({prev_c.purpose})",
                    exact_quote=prev_c.exact_quote
                ))

        return deltas

    @staticmethod
    def compute_telemetry_diff(
        prev_requests: List[NetworkSignalSchema],
        curr_requests: List[NetworkSignalSchema]
    ) -> TelemetryDelta:
        prev_tp = set(r.targetDomain for r in prev_requests if r.isThirdParty)
        curr_tp = set(r.targetDomain for r in curr_requests if r.isThirdParty)

        new_tp = list(curr_tp - prev_tp)
        removed_tp = list(prev_tp - curr_tp)

        curr_cats: Dict[str, int] = {}
        for r in curr_requests:
            if r.isThirdParty:
                curr_cats[r.category] = curr_cats.get(r.category, 0) + 1

        prev_cats: Dict[str, int] = {}
        for r in prev_requests:
            if r.isThirdParty:
                prev_cats[r.category] = prev_cats.get(r.category, 0) + 1

        cat_shifts: Dict[str, int] = {}
        for cat in set(list(curr_cats.keys()) + list(prev_cats.keys())):
            shift = curr_cats.get(cat, 0) - prev_cats.get(cat, 0)
            if shift != 0:
                cat_shifts[cat] = shift

        return TelemetryDelta(
            new_third_party_domains=new_tp,
            removed_third_party_domains=removed_tp,
            category_shifts=cat_shifts,
            net_tracker_count_delta=len(curr_tp) - len(prev_tp)
        )

    @classmethod
    def compare_snapshots(
        cls,
        domain: str,
        prev_score: Optional[int],
        curr_score: int,
        prev_claims: List[PolicyClaimSchema],
        curr_claims: List[PolicyClaimSchema],
        prev_requests: List[NetworkSignalSchema],
        curr_requests: List[NetworkSignalSchema]
    ) -> TemporalPostureComparison:
        claim_deltas = cls.compute_claim_diff(prev_claims, curr_claims)
        telemetry_delta = cls.compute_telemetry_diff(prev_requests, curr_requests)

        score_delta = curr_score - (prev_score if prev_score is not None else curr_score)
        if score_delta > 5:
            direction = "degraded"
        elif score_delta < -5:
            direction = "improved"
        else:
            direction = "stable"

        summary_parts = []
        if score_delta != 0:
            summary_parts.append(f"Risk score changed by {score_delta:+d} points.")
        if telemetry_delta.new_third_party_domains:
            summary_parts.append(f"Observed {len(telemetry_delta.new_third_party_domains)} new third-party domain(s).")
        if claim_deltas:
            summary_parts.append(f"Identified {len(claim_deltas)} semantic policy disclosure update(s).")
        if not summary_parts:
            summary_parts.append("Privacy posture remained stable across observation windows.")

        return TemporalPostureComparison(
            domain=domain,
            previous_score=prev_score,
            current_score=curr_score,
            score_delta=score_delta,
            posture_direction=direction,
            claim_deltas=claim_deltas,
            telemetry_delta=telemetry_delta,
            summary=" ".join(summary_parts)
        )

