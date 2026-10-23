from __future__ import annotations

import ipaddress
import re
from typing import Literal, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

RequestCategory = Literal["analytics", "advertising", "social", "cdn", "essential", "telemetry", "unknown"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def normalize_hostname(value: str) -> str:
    host = value.strip().rstrip(".").lower()
    if not host or len(host) > 253 or any(ch in host for ch in "/?#@\\"):
        raise ValueError("Expected a hostname")
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass
    if all(ch in "0123456789." for ch in host):
        raise ValueError("Ambiguous numeric hostnames are not allowed")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Invalid internationalized hostname") from exc
    labels = ascii_host.split(".")
    if any(not label or len(label) > 63 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) for label in labels):
        raise ValueError("Invalid hostname")
    return ascii_host


class NetworkSignalSchema(StrictSchema):
    requestId: Optional[str] = Field(default=None, max_length=128)
    url: str = Field(min_length=8, max_length=2048)
    targetDomain: str = Field(min_length=1, max_length=253)
    initiator: Optional[str] = Field(default=None, max_length=253)
    isThirdParty: bool
    category: RequestCategory
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"] = "GET"
    timestamp: Optional[int] = Field(default=None, ge=0, le=4_102_444_800_000)

    @field_validator("targetDomain")
    @classmethod
    def validate_target_domain(cls, value: str) -> str:
        return normalize_hostname(value)

    @field_validator("initiator")
    @classmethod
    def validate_initiator(cls, value: Optional[str]) -> Optional[str]:
        return normalize_hostname(value) if value else value

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Observation URL must be HTTP or HTTPS")
        return value


class StorageSignalSchema(StrictSchema):
    type: Literal["localStorage", "sessionStorage"]
    count: int = Field(ge=0, le=100_000)
    isThirdParty: bool = False
    persistent: bool


class ObservationIngestRequest(StrictSchema):
    domain: str = Field(min_length=1, max_length=253)
    scan_session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    requests: list[NetworkSignalSchema] = Field(default_factory=list, max_length=200)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        return normalize_hostname(value)


class ObservationIngestResponse(StrictSchema):
    status: Literal["ingested"]
    records_stored: int = Field(ge=0)
    third_party_count: int = Field(ge=0)
    unsupported_categories: list[Literal["storage", "permissions"]] = Field(default_factory=list)
