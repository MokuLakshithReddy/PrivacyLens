from typing import Optional, List
from pydantic import BaseModel, Field

class PolicyClaimSchema(BaseModel):
    claim_id: str
    category: str
    data_type: str
    purpose: str
    sharing: bool
    third_party: Optional[str] = None
    retention_specified: bool = False
    retention_period: Optional[str] = None
    section_name: str
    exact_quote: str
    confidence: float = Field(ge=0.0, le=1.0)

class PolicyDiscoverRequest(BaseModel):
    url: str

class PolicyDiscoverResponse(BaseModel):
    discovered: bool
    policy_url: Optional[str] = None
    source: str
    confidence: float

class PolicyAnalyzeRequest(BaseModel):
    domain: str
    policy_url: str
    policy_html: Optional[str] = None

class PolicyAnalyzeResponse(BaseModel):
    policy_id: str
    domain: str
    claims_count: int
    sections: List[str]
    claims: List[PolicyClaimSchema]
