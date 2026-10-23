from typing import Optional, List
from pydantic import ConfigDict, BaseModel, Field, field_validator
from app.schemas.observation import normalize_hostname


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PolicyClaimSchema(StrictSchema):
    claim_id: str = Field(max_length=128)
    category: str = Field(max_length=80)
    data_type: str = Field(max_length=200)
    purpose: str = Field(max_length=200)
    sharing: bool
    third_party: Optional[str] = Field(default=None, max_length=500)
    retention_specified: bool = False
    retention_period: Optional[str] = Field(default=None, max_length=200)
    section_name: str = Field(max_length=200)
    exact_quote: str = Field(max_length=5000)


class PolicyDiscoverRequest(StrictSchema):
    url: str = Field(min_length=8, max_length=2048)


class PolicyDiscoverResponse(BaseModel):
    discovered: bool
    policy_url: Optional[str] = None
    source: str


class PolicyAnalyzeRequest(StrictSchema):
    domain: str = Field(min_length=1, max_length=253)
    policy_url: str = Field(min_length=8, max_length=2048)
    policy_html: Optional[str] = Field(default=None, max_length=1_000_000)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        return normalize_hostname(value)


class PolicyAnalyzeResponse(BaseModel):
    policy_id: str
    domain: str
    analysis_method: str
    claims_count: int
    sections: List[str]
    claims: List[PolicyClaimSchema]
