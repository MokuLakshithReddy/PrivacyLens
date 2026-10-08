from typing import Optional, List
from pydantic import BaseModel

class NetworkSignalSchema(BaseModel):
    requestId: Optional[str] = None
    url: str
    targetDomain: str
    initiator: Optional[str] = None
    isThirdParty: bool
    category: str
    method: Optional[str] = "GET"
    timestamp: Optional[int] = None

class StorageSignalSchema(BaseModel):
    type: str
    name: str
    isThirdParty: bool
    persistent: bool
    byteLength: Optional[int] = None

class ObservationIngestRequest(BaseModel):
    domain: str
    tab_url: str
    requests: List[NetworkSignalSchema] = []
    storage_keys: List[StorageSignalSchema] = []
    permissions: List[str] = []

class ObservationIngestResponse(BaseModel):
    status: str
    records_stored: int
    third_party_count: int
