import asyncio
import json
import re
import logging
import uuid
from typing import List, Dict, Any
from app.ai.base import BaseAIProvider, PROMPT_INJECTION_DEFENSE_PROMPT
from app.config import settings
from app.schemas.policy import PolicyClaimSchema

logger = logging.getLogger(__name__)

class GeminiAIProvider(BaseAIProvider):
    def __init__(self):
        self.client = None
        if settings.gemini_api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=settings.gemini_api_key)
            except Exception:
                logger.warning("Google GenAI client could not be initialized")

    async def extract_claims_from_section(
        self,
        section_name: str,
        section_text: str
    ) -> List[PolicyClaimSchema]:
        if not self.client:
            return []

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
      }}
]

<UNTRUSTED_EXTERNAL_DOCUMENT>
{section_text[:4000]}
</UNTRUSTED_EXTERNAL_DOCUMENT>
"""
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"response_mime_type": "application/json", "max_output_tokens": 4096},
                ),
                timeout=20,
            )
            raw_text = response.text or "[]"
            if len(raw_text) > 20000:
                return []
            data = json.loads(raw_text)
            if not isinstance(data, list) or len(data) > 50:
                return []

            allowed = {"category", "data_type", "purpose", "sharing", "third_party",
                       "retention_specified", "retention_period", "exact_quote"}
            claims: List[PolicyClaimSchema] = []
            for item in data:
                if not isinstance(item, dict) or set(item) - allowed:
                    continue
                quote = item.get("exact_quote")
                if not isinstance(quote, str) or not quote:
                    continue
                normalize = lambda text: re.sub(r"\s+", " ", text).strip()
                if normalize(quote) not in normalize(section_text):
                    continue
                try:
                    claims.append(PolicyClaimSchema(
                        claim_id=f"clm_{uuid.uuid4().hex}",
                        category=str(item["category"]),
                        data_type=str(item["data_type"]),
                        purpose=str(item["purpose"]),
                        sharing=item["sharing"],
                        third_party=item.get("third_party"),
                        retention_specified=item["retention_specified"],
                        retention_period=item.get("retention_period"),
                        section_name=section_name,
                        exact_quote=quote,
                    ))
                except (KeyError, TypeError, ValueError):
                    continue
            return claims
        except Exception:
            logger.warning("Gemini claim extraction failed; no claims were accepted")
            return []

    async def generate_finding_rationale(
        self,
        gap_type: str,
        policy_quotes: List[str],
        observed_signals: List[Dict[str, Any]]
    ) -> str:
        if not self.client:
            return "No AI rationale was generated; inspect the attached evidence and rule outcome."

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
        except Exception:
            logger.warning("Gemini rationale generation failed")
            return "AI rationale unavailable; inspect the attached evidence and rule outcome."
