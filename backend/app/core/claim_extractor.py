import logging
from typing import List, Dict
from app.ai.base import BaseAIProvider
from app.ai.gemini_provider import GeminiAIProvider
from app.ai.mock_provider import MockAIProvider
from app.config import settings
from app.core.section_classifier import classify_section_category
from app.schemas.policy import PolicyClaimSchema

logger = logging.getLogger(__name__)

class ClaimExtractor:
    def __init__(self, provider: BaseAIProvider = None):
        if provider:
            self.provider = provider
        elif settings.default_ai_provider == "gemini":
            self.provider = GeminiAIProvider()
        else:
            self.provider = MockAIProvider()

    async def process_sections(self, sections: List[Dict[str, str]]) -> List[PolicyClaimSchema]:
        all_claims: List[PolicyClaimSchema] = []

        for sec in sections:
            title = sec["section_name"]
            text = sec["text"]
            category = classify_section_category(title, text[:300])

            try:
                claims = await self.provider.extract_claims_from_section(
                    section_name=f"{title} ({category})",
                    section_text=text
                )
                all_claims.extend(claims)
            except Exception as e:
                logger.error(f"Failed extracting claims from section '{title}': {e}")

        return all_claims
