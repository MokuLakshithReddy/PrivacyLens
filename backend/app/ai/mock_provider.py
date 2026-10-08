import re
import uuid
from typing import List, Dict, Any
from app.ai.base import BaseAIProvider
from app.schemas.policy import PolicyClaimSchema

class MockAIProvider(BaseAIProvider):
    """
    Deterministic rule-based mock provider.
    Runs locally at zero latency, extracts real verbatim quotes from the text.
    """

    async def extract_claims_from_section(
        self,
        section_name: str,
        section_text: str
    ) -> List[PolicyClaimSchema]:
        claims: List[PolicyClaimSchema] = []
        sentences = [s.strip() for s in re.split(r'[.\n]+', section_text) if len(s.strip()) > 15]

        for s in sentences:
            s_lower = s.lower()

            # Advertising / Sharing detection
            if any(k in s_lower for k in ['advertising', 'advertisers', 'ad partners', 'marketing partners', 'share with partners']):
                claims.append(PolicyClaimSchema(
                    claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                    category="third_party_sharing",
                    data_type="identifiers_and_activity",
                    purpose="advertising",
                    sharing=True,
                    third_party="advertising_networks",
                    retention_specified=False,
                    section_name=section_name,
                    exact_quote=s[:200],
                    confidence=0.91
                ))

            # Analytics detection
            elif any(k in s_lower for k in ['analytics', 'usage data', 'improve our services', 'measure traffic', 'statistical']):
                claims.append(PolicyClaimSchema(
                    claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                    category="data_collection",
                    data_type="usage_metrics",
                    purpose="analytics",
                    sharing=False,
                    retention_specified=False,
                    section_name=section_name,
                    exact_quote=s[:200],
                    confidence=0.88
                ))

            # Location / Geolocation detection
            elif any(k in s_lower for k in ['location', 'geolocation', 'gps', 'ip address']):
                claims.append(PolicyClaimSchema(
                    claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                    category="data_collection",
                    data_type="location",
                    purpose="service_delivery",
                    sharing=False,
                    retention_specified=False,
                    section_name=section_name,
                    exact_quote=s[:200],
                    confidence=0.86
                ))

            # Retention detection
            elif any(k in s_lower for k in ['retain', 'retention', 'delete', 'deletion', 'period']):
                claims.append(PolicyClaimSchema(
                    claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                    category="data_retention",
                    data_type="all_collected",
                    purpose="compliance",
                    sharing=False,
                    retention_specified=True,
                    retention_period="specified_in_policy",
                    section_name=section_name,
                    exact_quote=s[:200],
                    confidence=0.85
                ))

        # Ensure at least one baseline claim if text is substantial
        if not claims and len(section_text) > 50:
            sample_sentence = sentences[0] if sentences else section_text[:100]
            claims.append(PolicyClaimSchema(
                claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                category="general_notice",
                data_type="general",
                purpose="general_operations",
                sharing=False,
                retention_specified=False,
                section_name=section_name,
                exact_quote=sample_sentence[:200],
                confidence=0.75
            ))

        return claims

    async def generate_finding_rationale(
        self,
        gap_type: str,
        policy_quotes: List[str],
        observed_signals: List[Dict[str, Any]]
    ) -> str:
        domains = [s.get('targetDomain', '') for s in observed_signals if s.get('targetDomain')]
        dom_list = ", ".join(list(set(domains))[:3]) or "third-party endpoints"

        if gap_type == "omission_advertising":
            return (
                f"Active browser telemetry recorded network requests to advertising-categorized domain(s) ({dom_list}), "
                f"whereas the published privacy policy contains no explicit disclosure authorizing third-party advertising exchange distribution."
            )
        elif gap_type == "permission_mismatch":
            return (
                f"The web application attempted to query browser capabilities (e.g. geolocation/media) without a corresponding "
                f"explicit data collection disclosure in the published policy."
            )
        elif gap_type == "broad_language_concern":
            quote_sample = f'"{policy_quotes[0]}"' if policy_quotes else "broad clauses"
            return (
                f"Policy uses expansive or ambiguous terminology ({quote_sample}) while runtime behavior exhibits specific "
                f"third-party telemetry tracking across {dom_list}."
            )
        else:
            return (
                f"A divergence was detected between declared practices and runtime observed signals involving {dom_list}."
            )
