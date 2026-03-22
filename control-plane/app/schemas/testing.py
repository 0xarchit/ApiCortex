import uuid
from typing import Any, Literal

from pydantic import BaseModel, HttpUrl

class TestRequest(BaseModel):
    method: str
    url: HttpUrl
    headers: dict[str, str] | None = None
    body: Any | None = None


class ContractValidation(BaseModel):
    status: Literal["valid", "warning", "missing"]
    endpoint_id: uuid.UUID | None = None
    path: str
    method: str
    contract_hash: str | None = None
    observed_hash: str | None = None

class TestResponse(BaseModel):
    status: int
    time_ms: int
    size_bytes: int
    body: Any
    headers: dict[str, str]
    contract_validation: ContractValidation
