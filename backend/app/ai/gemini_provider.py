import json
import logging
import uuid
from typing import List, Dict, Any
from app.ai.base import BaseAIProvider, PROMPT_INJECTION_DEFENSE_PROMPT
from app.ai.mock_provider import MockAIProvider
from app.config import settings
from app.schemas.policy import PolicyClaimSchema

logger = logging.getLogger(__name__)

class GeminiAIProvider(BaseAIProvider):
    def __init__(self):
        self.fallback = MockAIProvider()
        self.client = None
        if settings.gemini_api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=settings.gemini_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}")

    async def extract_claims_from_section(
        self,
        section_name: str,
        section_text: str
    ) -> List[PolicyClaimSchema]:
        if not self.client:
            return await self.fallback.extract_claims_from_section(section_name, section_text)

        prompt = f"""
{PROMPT_INJECTION_DEFENSE_PROMPT}

Extract factual privacy claims from this section: "{section_name}".
Return ONLY a valid JSON list of objects matching this schema:
[
  {{
    "category": "data_collection" | "third_party_sharing" | "data_retention" | "user_rights" | "cookies",
    "data_type": "string",
    "purpose": "string",
    "sharing": boolean,
    "third_party": "string or null",
    "retention_specified": boolean,
    "retention_period": "string or null",
    "exact_quote": "exact quote from the document text",
    "confidence": float between 0.0 and 1.0
  }}
]

<UNTRUSTED_EXTERNAL_DOCUMENT>
{section_text[:4000]}
</UNTRUSTED_EXTERNAL_DOCUMENT>
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            raw_text = response.text or "[]"
            data = json.loads(raw_text)

            claims: List[PolicyClaimSchema] = []
            for item in data:
                # Security quote verification: check if quote exists in original text
                quote = item.get("exact_quote", "")
                if quote and quote in section_text:
                    confidence = float(item.get("confidence", 0.85))
                else:
                    # Slightly penalize unverified quote
                    confidence = float(item.get("confidence", 0.70)) * 0.8

                claims.append(PolicyClaimSchema(
                    claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                    category=item.get("category", "data_collection"),
                    data_type=item.get("data_type", "general"),
                    purpose=item.get("purpose", "general"),
                    sharing=bool(item.get("sharing", False)),
                    third_party=item.get("third_party"),
                    retention_specified=bool(item.get("retention_specified", False)),
                    retention_period=item.get("retention_period"),
                    section_name=section_name,
                    exact_quote=quote[:250],
                    confidence=min(1.0, max(0.0, confidence))
                ))
            return claims if claims else await self.fallback.extract_claims_from_section(section_name, section_text)
        except Exception as e:
            logger.warning(f"Gemini claim extraction failed, using fallback: {e}")
            return await self.fallback.extract_claims_from_section(section_name, section_text)

    async def generate_finding_rationale(
        self,
        gap_type: str,
        policy_quotes: List[str],
        observed_signals: List[Dict[str, Any]]
    ) -> str:
        if not self.client:
            return await self.fallback.generate_finding_rationale(gap_type, policy_quotes, observed_signals)

        prompt = f"""
{PROMPT_INJECTION_DEFENSE_PROMPT}

Write a 2-sentence objective, evidence-based security explanation explaining this detected privacy gap:
Gap Type: {gap_type}
Declared Policy Quotes: {json.dumps(policy_quotes)}
Observed Browser Signals: {json.dumps(observed_signals[:5])}

Do NOT accuse the website of legal violations. Use terms such as 'Candidate gap', 'Divergence between declared policy and observed endpoints', 'Potential alignment concern'.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return (response.text or "").strip()
        except Exception as e:
            logger.warning(f"Gemini rationale synthesis failed, using fallback: {e}")
            return await self.fallback.generate_finding_rationale(gap_type, policy_quotes, observed_signals)
