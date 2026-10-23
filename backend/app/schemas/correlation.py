from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class FindingEvidenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policyQuotes: List[str] = Field(default_factory=list, max_length=10)
    policyLocations: List[dict[str, int]] = Field(default_factory=list, max_length=10)
    disclosureStatus: str = "insufficient_evidence"
    observedDomains: List[str] = Field(default_factory=list, max_length=100)
    observedEventIds: List[str] = Field(default_factory=list, max_length=100)
    observedStorageCount: Optional[int] = Field(default=None, ge=0)
    observedPermissions: Optional[List[str]] = None


class EvidenceFindingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findingId: str
    scanSessionId: str
    policyVersionId: str
    ruleId: str
    ruleVersion: str
    gapType: str
    severity: str
    title: str
    rationale: str
    evidence: FindingEvidenceSchema


class ThirdPartyNodeSchema(BaseModel):
    domain: str
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
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    domain: str = Field(min_length=1, max_length=253)
    scan_session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    policy_url: Optional[str] = Field(default=None, max_length=2048)


class SiteAnalysisResultSchema(BaseModel):
    domain: str
    policyUrl: Optional[str] = None
    inspectedAt: str
    riskScore: int = Field(ge=0, le=100)
    riskTier: str
    evidenceCoverage: float = Field(ge=0.0, le=1.0)
    riskFactors: dict[str, int]
    riskWeights: dict[str, float]
    algorithmVersion: str
    evaluationMode: str = "backend"
    summary: str
    claimsCount: int
    observedThirdPartiesCount: int
    findings: List[EvidenceFindingSchema]
    dataFlow: DataFlowSchema
    temporalChange: Optional[TemporalChangeSchema] = None
