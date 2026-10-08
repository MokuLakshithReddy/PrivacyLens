from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class FindingEvidenceSchema(BaseModel):
    policyQuotes: List[str] = []
    observedDomains: List[str] = []
    observedStorageKeys: Optional[List[str]] = None
    observedPermissions: Optional[List[str]] = None

class EvidenceFindingSchema(BaseModel):
    findingId: str
    gapType: str
    severity: str
    confidence: float
    title: str
    rationale: str
    evidence: FindingEvidenceSchema

class ThirdPartyNodeSchema(BaseModel):
    domain: string if False else str
    category: str
    requestCount: int
    disclosedInPolicy: bool

class DataFlowSchema(BaseModel):
    firstParty: str
    thirdParties: List[ThirdPartyNodeSchema]

class TemporalChangeSchema(BaseModel):
    previousScore: Optional[int] = None
    scoreDelta: Optional[int] = None
    newThirdParties: Optional[List[str]] = None

class CorrelateRequest(BaseModel):
    domain: str
    policy_url: Optional[str] = None

class SiteAnalysisResultSchema(BaseModel):
    domain: str
    policyUrl: Optional[str] = None
    inspectedAt: str
    riskScore: int = Field(ge=0, le=100)
    riskTier: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    claimsCount: int
    observedThirdPartiesCount: int
    findings: List[EvidenceFindingSchema]
    dataFlow: DataFlowSchema
    temporalChange: Optional[TemporalChangeSchema] = None
