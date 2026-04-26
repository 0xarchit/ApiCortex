"""Request and response schemas for API management endpoints."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, HttpUrl


class APICreate(BaseModel):
    """Request schema for creating a new API."""
    name: str
    base_url: HttpUrl


class APIUpdate(BaseModel):
    """Request schema for updating an existing API."""
    name: str | None = None
    base_url: HttpUrl | None = None


class APIOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    base_url: str
    created_at: datetime


class EndpointCreate(BaseModel):
    path: str
    method: str
    monitoring_enabled: bool = True
    poll_interval_seconds: int | None = None
    timeout_ms: int | None = None
    poll_headers_json: dict[str, str] | None = None


class EndpointDirectCreate(EndpointCreate):
    api_id: uuid.UUID


class EndpointUpdate(BaseModel):
    path: str | None = None
    method: str | None = None
    monitoring_enabled: bool | None = None
    poll_interval_seconds: int | None = None
    timeout_ms: int | None = None
    poll_headers_json: dict[str, str] | None = None


class EndpointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    api_id: uuid.UUID
    path: str
    method: str
    monitoring_enabled: bool
    consecutive_error_count: int = 0
    auto_paused: bool = False
    poll_interval_seconds: int | None = None
    timeout_ms: int | None = None
    poll_headers_json: dict[str, str] | None = None
    created_at: datetime
    updated_at: datetime


class OpenAPISpecCreate(BaseModel):
    version: str
    raw_spec: dict[str, Any]


class OpenAPIUploadRequest(BaseModel):
    api_id: uuid.UUID | None = None
    api_name: str | None = None
    base_url: HttpUrl | None = None
    version: str
    raw_spec: dict[str, Any]


class OpenAPIUploadOut(BaseModel):
    spec_id: uuid.UUID
    api_id: uuid.UUID
    version: str
    uploaded_at: datetime
    api_created: bool
    endpoints_synced: int


class OpenAPISpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    api_id: uuid.UUID
    version: str
    uploaded_at: datetime


class ContractCreate(BaseModel):
    schema_hash: str


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    endpoint_id: uuid.UUID
    schema_hash: str
    created_at: datetime


class DashboardSummaryOut(BaseModel):
    p95_latency_ms: float
    error_rate: float
    request_count: int


class DashboardNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message: str
    severity: str
    source: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class DashboardNotificationReadAllOut(BaseModel):
    updated: int
